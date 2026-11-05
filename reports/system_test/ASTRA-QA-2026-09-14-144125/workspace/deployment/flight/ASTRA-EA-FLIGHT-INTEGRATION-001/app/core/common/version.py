"""Standardized version and build metadata for ASTRA-EA."""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any, Dict

VERSION = "1.0.0"
SYSTEM_NAME = "ASTRA-EA"
TAGLINE = "See. Understand. Verify. Assist. Record. — Locally, in Space."
PROBLEM_STATEMENT = "SIH26174 — AI Human Activity Recognition for On-board BAS Experiments"


def get_git_commit() -> str:
    """Retrieve active git commit hash or return 'unknown' if unavailable."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        ).strip()
        return commit
    except Exception:
        return "unknown"


def get_version_metadata() -> Dict[str, Any]:
    """Compile comprehensive software build and runtime version dictionary."""
    return {
        "system_name": SYSTEM_NAME,
        "version": VERSION,
        "git_commit": get_git_commit(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "build_identifier": f"{VERSION}-{get_git_commit()[:7]}",
        "tagline": TAGLINE,
        "problem_statement": PROBLEM_STATEMENT,
    }
