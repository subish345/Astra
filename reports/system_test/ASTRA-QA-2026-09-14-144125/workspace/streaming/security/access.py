# ==============================================================================
# ASTRA-EA Streaming Security & Access Control
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Security validation for bind addresses, evidence file paths, and request payloads."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Optional


def is_safe_bind_address(host: str, allow_lan: bool = True) -> bool:
    """Validate that host address conforms to local/LAN air-gap policies.

    Default policy allows loopback (127.0.0.1, ::1) and RFC 1918 private LAN addresses.
    Rejects public routable IP addresses unless explicitly configured.
    """
    if host in ("localhost", "127.0.0.1", "::1"):
        return True

    if host == "0.0.0.0":
        return allow_lan

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            return True
        if allow_lan and ip.is_private:
            return True
        return False
    except ValueError:
        # If hostname is not an IP, only localhost is allowed by default
        return host == "localhost"


def sanitize_evidence_id(evidence_id: str) -> Optional[str]:
    """Sanitize and validate evidence identifier to prevent path traversal attacks.

    Ensures identifier contains only alphanumeric characters, underscores, and hyphens.
    Returns safe string or None if malicious/malformed.
    """
    if not evidence_id or len(evidence_id) > 128:
        return None

    # Strict regex: alphanumeric, underscores, hyphens, and optional .json extension
    if not re.match(r"^[A-Za-z0-9_\-]+(?:\.json)?$", evidence_id):
        return None

    # Path traversal check
    if ".." in evidence_id or "/" in evidence_id or "\\" in evidence_id:
        return None

    return Path(evidence_id).name
