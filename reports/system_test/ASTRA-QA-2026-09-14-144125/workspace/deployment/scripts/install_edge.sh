#!/usr/bin/env bash
# ==============================================================================
# ASTRA-EA Edge Deployment Installation Script
# Target: Embedded Linux (x86_64, aarch64, ARM64)
# ==============================================================================

set -e

echo "============================================================"
echo " ASTRA-EA EDGE DEPLOYMENT INSTALLER"
echo "============================================================"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

echo "[1/5] Verifying Python Runtime..."
python3 --version

echo "[2/5] Creating Edge Working & Data Directories..."
mkdir -p data/runs data/dataset storage/database storage/video storage/evidence reports/edge reports/physical reports/hil

echo "[3/5] Installing Core Package in Editable / Edge Mode..."
pip install -e . --no-deps 2>/dev/null || pip install -e .

echo "[4/5] Initializing Local SQLite Telemetry Database..."
astra db init

echo "[5/5] Running Edge Hardware Diagnostic Check..."
astra edge doctor

echo "============================================================"
echo " EDGE INSTALLATION COMPLETE"
echo " Launch Edge Demonstration via: astra physical-test"
echo "============================================================"
