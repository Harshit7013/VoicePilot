/**
 * ConfirmationDialog — modal for high/medium risk action approval.
 */

import type { FC } from 'react';
import type { ConfirmationRequest } from '../hooks/useVoicePilot';
import { AlertTriangle, Lock } from 'lucide-react';

interface ConfirmationDialogProps {
  request: ConfirmationRequest;
  onConfirm: (id: string, approved: boolean) => void;
}

const HIGH_RISK_ACTIONS = new Set(['delete_file', 'delete_directory']);

export const ConfirmationDialog: FC<ConfirmationDialogProps> = ({ request, onConfirm }) => {
  const isHigh = HIGH_RISK_ACTIONS.has(request.action);
  const icon = isHigh ? <AlertTriangle size={32} className="text-danger" /> : <Lock size={32} className="text-warning" />;
  const title = isHigh ? 'High-Risk Action' : 'Action Confirmation';

  return (
    <div className="confirmation-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="confirmation-dialog">
        <div className="confirmation-icon">{icon}</div>
        <h2 id="confirm-title" className="confirmation-title">{title}</h2>
        <pre className="confirmation-message">{request.message}</pre>
        <div className="confirmation-actions">
          <button
            id="confirm-deny-btn"
            className="btn btn-ghost"
            onClick={() => onConfirm(request.confirmation_id, false)}
            autoFocus={isHigh}
          >
            ✕ Deny
          </button>
          <button
            id="confirm-approve-btn"
            className={`btn ${isHigh ? 'btn-danger' : 'btn-success'}`}
            onClick={() => onConfirm(request.confirmation_id, true)}
            autoFocus={!isHigh}
          >
            ✓ Approve
          </button>
        </div>
      </div>
    </div>
  );
};
