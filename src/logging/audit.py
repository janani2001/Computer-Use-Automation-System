"""Structured JSON audit events for discovery, replay, and human handoff."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.safety.redaction import redact


class AuditLogger:
    """Writes redacted, correlation-friendly JSON events to an append-only file."""

    def __init__(self, log_path: Optional[Path] = None, run_id: Optional[str] = None):
        self.log_path = log_path or Path("logs/audit.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or uuid.uuid4().hex
        self.logger = logging.getLogger("audit")

    def event(self, event_type: str, **fields: Any) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event_type": event_type,
            **fields,
        }
        redacted = json.loads(redact(json.dumps(record, default=str)))
        with self.log_path.open("a") as handle:
            handle.write(json.dumps(redacted, sort_keys=True) + "\n")
        self.logger.info("audit event=%s run_id=%s", event_type, self.run_id)
        return redacted
