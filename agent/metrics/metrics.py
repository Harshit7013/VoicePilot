"""
Metrics module — records task history, execution events, and reliability metrics in SQLite.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/voicepilot.db")


class MetricsStore:
    """
    SQLite-backed store for task history and reliability metrics.
    Uses aiosqlite for non-blocking I/O.
    """

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._conn = None

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            import aiosqlite
            self._conn = await aiosqlite.connect(self.db_path)
            await self._create_tables()
            logger.info(f"Metrics DB connected: {self.db_path}")
        except ImportError:
            logger.warning("aiosqlite not installed. Metrics will not be persisted.")

    async def _create_tables(self):
        if self._conn is None:
            return
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                status TEXT NOT NULL,
                success INTEGER NOT NULL,
                duration_seconds REAL,
                total_retries INTEGER DEFAULT 0,
                error TEXT,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS execution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_index INTEGER,
                action TEXT,
                success INTEGER,
                output TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0,
                timestamp REAL NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_index INTEGER,
                stage TEXT,
                success INTEGER,
                timestamp REAL NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
        """)
        await self._conn.commit()

    async def record_task_start(self, task_id: str, task: str) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO tasks (id, task, status, success, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, task, "running", 0, time.time()),
        )
        await self._conn.commit()

    async def record_task_complete(
        self,
        task_id: str,
        success: bool,
        duration: float,
        retries: int,
        error: Optional[str] = None,
    ) -> None:
        if self._conn is None:
            return
        status = "success" if success else "failed"
        await self._conn.execute(
            """UPDATE tasks SET status=?, success=?, duration_seconds=?, total_retries=?, error=?
               WHERE id=?""",
            (status, int(success), duration, retries, error, task_id),
        )
        await self._conn.commit()

    async def record_event(
        self,
        task_id: str,
        step_index: int,
        action: str,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        retry_count: int = 0,
        verified: bool = False,
    ) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            """INSERT INTO execution_events
               (task_id, step_index, action, success, output, error, retry_count, verified, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id, step_index, action, int(success),
                json.dumps(output) if output is not None else None,
                error, retry_count, int(verified), time.time(),
            ),
        )
        await self._conn.commit()

    async def record_recovery(self, task_id: str, step_index: int, stage: str, success: bool) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO recovery_attempts (task_id, step_index, stage, success, timestamp) VALUES (?, ?, ?, ?, ?)",
            (task_id, step_index, stage, int(success), time.time()),
        )
        await self._conn.commit()

    async def get_metrics_summary(self) -> Dict[str, Any]:
        if self._conn is None:
            return {
                "total_tasks": 0,
                "successful_tasks": 0,
                "task_success_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "avg_retries": 0.0,
                "verified_steps": 0,
            }

        async with self._conn.execute(
            "SELECT COUNT(*), SUM(success), AVG(duration_seconds), AVG(total_retries) FROM tasks"
        ) as cursor:
            row = await cursor.fetchone()
            total, successes, avg_duration, avg_retries = row

        async with self._conn.execute(
            "SELECT COUNT(*) FROM execution_events WHERE verified=1"
        ) as cursor:
            verified_row = await cursor.fetchone()

        task_success_rate = (successes / total * 100) if total else 0

        return {
            "total_tasks": total or 0,
            "successful_tasks": successes or 0,
            "task_success_rate": round(task_success_rate, 1),
            "avg_duration_seconds": round(avg_duration or 0, 2),
            "avg_retries": round(avg_retries or 0, 2),
            "verified_steps": verified_row[0] if verified_row else 0,
        }

    async def get_recent_tasks(self, limit: int = 20) -> List[Dict]:
        if self._conn is None:
            return []
        async with self._conn.execute(
            "SELECT id, task, status, success, duration_seconds, total_retries, error, created_at "
            "FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            keys = ["id", "task", "status", "success", "duration_seconds", "total_retries", "error", "created_at"]
            return [dict(zip(keys, row)) for row in rows]

    async def close(self):
        if self._conn:
            await self._conn.close()
