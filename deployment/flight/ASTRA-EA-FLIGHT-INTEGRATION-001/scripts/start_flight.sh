#!/usr/bin/env bash
# ASTRA-EA Flight-Integration Startup Script
export ASTRA_RUNTIME_MODE="FLIGHT_INTEGRATION"
export ASTRA_PLATFORM_PROFILE="FLIGHT_TARGET_TBD"
python3 -m app.core.flight.startup
