"""
Redaction - masks sensitive-looking values before they reach logs or evidence files.

Banking data (account numbers, balances) should never sit in plain text in a
log file. This is a small, dependency-free utility so every logging call site
in the project can redact consistently.
"""

import re

_ACCOUNT_LIKE_NUMBER = re.compile(r"\b\d{6,}\b")


def redact(text: str) -> str:
    """Mask long digit sequences (account/member numbers) in log-bound text."""
    return _ACCOUNT_LIKE_NUMBER.sub("[REDACTED]", text)
