#!/usr/bin/env python3
"""ASTRA-EA Root Entrypoint.

Delegates commands to the core CLI.
"""

from __future__ import annotations

import sys
from core.cli.commands import cli

if __name__ == "__main__":
    cli()
