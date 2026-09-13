#!/usr/bin/env python3
# ==============================================================================
# ASTRA-EA Ground Monitor Executable Entrypoint
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""CLI launcher for the standalone ASTRA-EA Ground Monitor application."""

from __future__ import annotations

import argparse
import os
import sys

# Ensure OpenCV / Qt uses XCB platform plugin under Wayland / X11
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication

from apps.ground_monitor.app import GroundMonitorWindow
from core.common.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="ASTRA-EA Ground Observability Console")
    parser.add_argument("--stream-url", type=str, default=None, help="URL of remote video stream")
    parser.add_argument("--events-url", type=str, default=None, help="URL of remote telemetry SSE events")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    args = parser.parse_args()

    # Load defaults from system configuration
    try:
        cfg = load_config()
        default_stream = cfg.ground_monitor.stream_url
        default_events = cfg.ground_monitor.events_url
    except Exception:
        default_stream = "http://127.0.0.1:8554/video"
        default_events = "http://127.0.0.1:8765/events"

    stream_url = args.stream_url or default_stream
    events_url = args.events_url or default_events

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("ASTRA-EA Ground Monitor")
    app.setOrganizationName("ISRO-SIH")

    window = GroundMonitorWindow(stream_url=stream_url, events_url=events_url)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
