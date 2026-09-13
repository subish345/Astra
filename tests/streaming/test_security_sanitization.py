# ==============================================================================
# ASTRA-EA Security & Sanitization Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Validates path traversal prevention, bind address enforcement, and rate limiting."""

from __future__ import annotations

import pytest

from streaming.security.access import is_safe_bind_address, sanitize_evidence_id
from streaming.security.rate_limit import ConnectionRateLimiter


def test_path_traversal_sanitization() -> None:
    """Ensure directory traversal attacks are neutralized."""
    assert sanitize_evidence_id("../../../etc/passwd") is None
    assert sanitize_evidence_id("..\\..\\windows\\system32") is None
    assert sanitize_evidence_id("EVT_001/../../secret") is None
    assert sanitize_evidence_id("valid_id_123") == "valid_id_123"
    assert sanitize_evidence_id("EVT_00124.json") == "EVT_00124.json"
    assert sanitize_evidence_id("") is None
    assert sanitize_evidence_id("A" * 200) is None  # Oversized


def test_bind_address_air_gap_validation() -> None:
    """Ensure public IP addresses cannot be bound by default."""
    assert is_safe_bind_address("127.0.0.1", allow_lan=False) is True
    assert is_safe_bind_address("localhost", allow_lan=False) is True
    assert is_safe_bind_address("8.8.8.8", allow_lan=True) is False
    assert is_safe_bind_address("1.1.1.1", allow_lan=True) is False
    # Private LAN
    assert is_safe_bind_address("192.168.1.100", allow_lan=True) is True
    assert is_safe_bind_address("10.0.0.1", allow_lan=True) is True


def test_rate_limiter() -> None:
    """Verify sliding window connection rate limiting."""
    limiter = ConnectionRateLimiter(max_requests_per_window=3, window_seconds=10.0)
    ip = "192.168.1.15"

    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    # 4th request in window must be blocked
    assert limiter.is_allowed(ip) is False
