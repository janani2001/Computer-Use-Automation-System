"""
Error policy - looks up how an artifact wants one specific step's failure handled.

Backed entirely by the artifact's own `error_handlers` list (see
schema.ErrorHandler) - the recipe itself declares its recovery strategy per
step. If a step has no declared handler, ReplayEngine treats that as
"escalate": failing safe by default instead of silently retrying or skipping.
"""

from typing import Optional

from src.artifacts.schema import CapabilityArtifact, ErrorHandler


class ErrorPolicy:
    """Resolves the declared ErrorHandler (if any) for a failed step."""

    def resolve(self, artifact: CapabilityArtifact, step_id: str) -> Optional[ErrorHandler]:
        for handler in artifact.error_handlers:
            if handler.step_id == step_id:
                return handler
        return None
