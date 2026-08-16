"""
Escalation handler - routes unrecoverable replay failures to a human.

Instead of silently failing, this writes an append-only audit record that a
human operator (or a downstream ticketing system) reads. `evidence/` is
already this project's designated home for saved runs, logs, and screenshots.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.artifacts.schema import AutomationStep

logger = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = Path("evidence/escalations.jsonl")


class EscalationHandler:
    """Records escalations for human follow-up."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or _DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def escalate(self, artifact_id: str, step: AutomationStep, reason: str) -> Dict[str, str]:
        """Append an escalation record and return it."""
        record = {
            "artifact_id": artifact_id,
            "step_id": step.id,
            "action": step.action,
            "reason": reason,
            "escalated_at": datetime.now().isoformat(),
        }
        with self.log_path.open("a") as handle:
            handle.write(json.dumps(record) + "\n")

        logger.warning(f"🆘 Escalated step '{step.id}' of artifact '{artifact_id}': {reason}")
        return record
