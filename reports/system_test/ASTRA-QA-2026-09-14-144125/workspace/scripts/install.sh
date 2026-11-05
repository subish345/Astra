#!/usr/bin/env bash
# ==============================================================================
# ASTRA-EA — Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# Production & Demonstration Installation Script
# ==============================================================================

set -e

echo "================================================================================"
echo " ASTRA-EA SYSTEM INSTALLATION & ENVIRONMENT INITIALIZATION"
echo "================================================================================"

# 1. Check Python version >= 3.11
REQUIRED_MAJOR=3
REQUIRED_MINOR=11

PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "[!] Error: python3 is not installed or not in PATH."
    exit 1
fi

PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

echo "[+] Detected Python version: $PY_VERSION"
if [ "$PY_MAJOR" -lt "$REQUIRED_MAJOR" ] || ([ "$PY_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PY_MINOR" -lt "$REQUIRED_MINOR" ]); then
    echo "[!] Error: Python >= 3.11 is required. Found $PY_VERSION."
    exit 1
fi

# 2. Install editable package
echo "[+] Installing ASTRA-EA package in active environment..."
$PYTHON_CMD -m pip install -e .

# 3. Create standardized product directories
echo "[+] Initializing standardized data & storage directories..."
mkdir -p data/runs data/recordings data/evidence/snapshots data/evidence/clips data/evidence/metadata data/reports data/logs storage/database storage/reports/benchmark storage/reports/simulation

# 4. Copy .env.example to .env if not present
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[+] Creating .env from .env.example..."
    cp .env.example .env
fi

# 5. Initialize database
echo "[+] Initializing SQLite database schema..."
$PYTHON_CMD main.py db init

# 6. Run deployment readiness diagnostic
echo "[+] Running system readiness verification..."
if command -v astra &> /dev/null; then
    astra doctor
else
    $PYTHON_CMD main.py doctor
fi

echo "================================================================================"
echo " ASTRA-EA INSTALLATION COMPLETE"
echo " Canonical Commands:"
echo "   astra doctor             # Run system diagnostics"
echo "   astra demo               # Launch one-command interactive demo"
echo "   astra mission            # Launch full onboard mission console"
echo "   astra ground-monitor     # Launch remote ground monitoring station"
echo "================================================================================"
