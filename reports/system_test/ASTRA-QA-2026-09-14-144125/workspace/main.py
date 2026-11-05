#!/usr/bin/env python3
"""ASTRA-EA Root Entrypoint.

Delegates commands to the core CLI.
"""

from __future__ import annotations

import os
import sys

# Ensure OpenCV / Qt uses XCB platform plugin under Wayland / X11 environments
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from core.cli.commands import cli

if __name__ == "__main__":
    cli()
