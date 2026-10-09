"""
Basic tests for the VoicePilot agent components.
Run with: PYTHONPATH=. .venv/bin/pytest tests/ -v
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from agent.planner import Planner, ActionPlan, RiskLevel
from agent.safety import RiskClassifier, PolicyGate
from agent.executor.file_ops import FileExecutor, _resolve
from agent.recovery import RecoveryManager
from agent.providers import MockSTTProvider, MockLLMProvider, MockTTSProvider


class TestLLMPlanner(unittest.TestCase):
    def test_prompt_generation(self):
        planner = Planner(llm=MockLLMProvider())
        prompt = planner._build_prompt("Create hello.py on Desktop")
        self.assertIn("Create hello.py on Desktop", prompt)
        self.assertIn("JSON", prompt)

    def test_plan_parsing_valid_json(self):
        planner = Planner(llm=MockLLMProvider())
        raw_json_str = json.dumps({
            "task": "Create file",
            "steps": [
                {"action": "open_application", "application": "Visual Studio Code"},
                {"action": "create_file", "path": "~/Desktop/hello.py"},
                {"action": "write_file", "path": "~/Desktop/hello.py", "content": "print('hello')"},
                {"action": "verify_file", "path": "~/Desktop/hello.py"}
            ]
        })
        extracted = planner._extract_json(raw_json_str)
        plan = ActionPlan.model_validate(extracted)
        self.assertEqual(plan.task, "Create file")
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.steps[0]["action"], "open_application")
        self.assertEqual(plan.steps[1]["action"], "create_file")


class TestLocalOfflineLLM(unittest.TestCase):
    def test_offline_hackathon_demo_task_1(self):
        from agent.providers.local_llm import LocalOfflineLLMProvider
        llm = LocalOfflineLLMProvider()
        res = asyncio.run(llm.complete("Create a folder named Hackathon Demo with a text file saying VoicePilot works offline."))
        data = json.loads(res.content)
        self.assertIn("Hackathon Demo", data["task"])
        self.assertEqual(len(data["steps"]), 4)
        self.assertEqual(data["steps"][0]["action"], "create_directory")

    def test_offline_calculator_task(self):
        from agent.providers.local_llm import LocalOfflineLLMProvider
        llm = LocalOfflineLLMProvider()
        res = asyncio.run(llm.complete("Open Calculator and calculate 125 x 48."))
        data = json.loads(res.content)
        self.assertEqual(data["steps"][0]["action"], "open_application")
        self.assertEqual(data["steps"][0]["application"], "Calculator")

    def test_offline_vscode_task(self):
        from agent.providers.local_llm import LocalOfflineLLMProvider
        llm = LocalOfflineLLMProvider()
        res = asyncio.run(llm.complete("Open Visual Studio Code, create hello.py, and verify that the file exists."))
        data = json.loads(res.content)
        self.assertEqual(data["steps"][0]["action"], "open_application")
        self.assertEqual(data["steps"][1]["action"], "create_file")


class TestRiskClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = RiskClassifier()

    def test_low_risk_actions(self):
        low_steps = [
            {"action": "open_application", "application": "Calculator"},
            {"action": "read_file", "path": "/tmp/test.txt"},
            {"action": "browser_search", "query": "python tutorial"},
            {"action": "verify_file", "path": "/tmp/test.txt"},
        ]
        for step in low_steps:
            risk = self.classifier.classify(step)
            self.assertEqual(risk, RiskLevel.LOW, f"Failed for action: {step['action']}")

    def test_medium_risk_actions(self):
        med_steps = [
            {"action": "create_file", "path": "~/Desktop/test.py"},
            {"action": "move_file", "source": "/tmp/a", "destination": "/tmp/b"},
            {"action": "write_file", "path": "~/Desktop/test.py", "content": "hello"},
        ]
        for step in med_steps:
            risk = self.classifier.classify(step)
            self.assertEqual(risk, RiskLevel.MEDIUM, f"Failed for action: {step['action']}")

    def test_high_risk_actions(self):
        high_steps = [
            {"action": "delete_file", "path": "~/Desktop/important.doc"},
            {"action": "delete_directory", "path": "~/Desktop/important"},
        ]
        for step in high_steps:
            risk = self.classifier.classify(step)
            self.assertEqual(risk, RiskLevel.HIGH, f"Failed for action: {step['action']}")


class TestPolicyGate(unittest.TestCase):
    def test_low_risk_auto_approve(self):
        classifier = RiskClassifier()
        callback = AsyncMock(return_value=True)
        gate = PolicyGate(classifier=classifier, confirmation_callback=callback)
        step = {"action": "open_application", "application": "Calculator"}
        approved = asyncio.run(gate.check(step, task="Open Calculator"))
        self.assertTrue(approved)
        callback.assert_not_called()

    def test_high_risk_requires_confirmation(self):
        classifier = RiskClassifier()
        callback = AsyncMock(return_value=True)
        gate = PolicyGate(classifier=classifier, confirmation_callback=callback)
        step = {"action": "delete_file", "path": "~/Desktop/important.doc"}
        approved = asyncio.run(gate.check(step, task="Delete file"))
        self.assertTrue(approved)
        callback.assert_called_once()


class TestFileExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = FileExecutor()

    def test_path_expansion(self):
        expanded = _resolve("~/Desktop/test.txt")
        self.assertTrue(str(expanded).endswith("/Desktop/test.txt"))
        self.assertFalse(str(expanded).startswith("~"))

    def test_unsupported_action(self):
        step = {"action": "unknown_action"}
        result = asyncio.run(self.executor.execute(step))
        self.assertFalse(result["success"])
        self.assertIn("Unknown file action", result["error"])


class TestRecoveryManager(unittest.TestCase):
    def setUp(self):
        self.recovery = RecoveryManager()

    def test_alternative_mapping(self):
        step = {"action": "click", "target": "Save"}
        alt = self.recovery._get_alternative(step)
        self.assertIsNotNone(alt)
        self.assertEqual(alt["action"], "press_key")


if __name__ == '__main__':
    unittest.main()
