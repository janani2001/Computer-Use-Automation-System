"""
Parameter resolver - Validates inputs and substitutes ${param} placeholders.

An artifact's steps reference parameters like "${member_id}" inside a step's
`value` field. This module is the only place that knows how that
placeholder syntax works.
"""

import re
from typing import Dict

from src.artifacts.schema import CapabilityArtifact

_PLACEHOLDER_PATTERN = re.compile(r"\$\{(\w+)\}")


class MissingParameterError(Exception):
    """Raised when a required artifact parameter was not supplied."""


class UnresolvedPlaceholderError(Exception):
    """Raised when a step references a parameter that has no value yet."""


class ParameterResolver:
    """Validates and substitutes ${param} placeholders against a value context."""

    def validate_required(self, artifact: CapabilityArtifact, params: Dict[str, str]) -> None:
        """
        Ensure every required parameter declared by the artifact was supplied.

        Raises:
            MissingParameterError: if any required parameter is absent.
        """
        missing = [
            name
            for name, definition in artifact.parameters.items()
            if definition.required and name not in params
        ]
        if missing:
            raise MissingParameterError(f"Missing required parameters: {missing}")

    def resolve(self, value: str, context: Dict[str, str]) -> str:
        """
        Replace every "${name}" placeholder in `value` with context[name].

        Raises:
            UnresolvedPlaceholderError: if a referenced name is not in context.
        """

        def _substitute(match: "re.Match[str]") -> str:
            name = match.group(1)
            if name not in context:
                raise UnresolvedPlaceholderError(f"Unresolved parameter reference: '${{{name}}}'")
            return context[name]

        return _PLACEHOLDER_PATTERN.sub(_substitute, value)
