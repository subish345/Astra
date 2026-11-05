# Repository Audit

Canonical entrypoint is `python3 main.py` / installed `astra`, implemented by `core.cli.commands:cli`. Active procedure is `configs/experiments/demo.yaml`, `DEMO_EXP_001` v1.0.0, with four ordered steps and MAIN_BOX, RED_BOX, YELLOW_BOX, WORK_SURFACE. Default object detection is `ColorSpatialObjectDetector`; MediaPipe PoseLandmarker Lite task asset is present. Mission Console is `core/ui/main_window.py`; Ground Monitor is `apps/ground_monitor/app.py`; persistence is SQLite plus `core/mission/recording.py` and `core/evidence/store.py`.

The repository was already dirty before this campaign. No reset, checkout, model replacement or deletion was performed.
