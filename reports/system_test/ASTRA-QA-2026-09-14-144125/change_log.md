# Change Log

| Time | Files | Reason / defect | Verification |
|---|---|---|---|
| 2026-09-14 | `core/perception/pose/mediapipe_adapter.py` | Visibility `None`/zero was converted to full confidence | `test_zero_visibility_never_becomes_confident_hand` |
| 2026-09-14 | `core/perception/factory.py`, `core/ui/worker.py`, `core/cli/commands.py` | Mission Console used legacy pose path despite MediaPipe availability | Live run reported MediaPipe 33 landmarks; targeted tests |
| 2026-09-14 | `core/ui/worker.py`, `core/ui/main_window.py` | Stop used unsupported wait keyword and cleanup status was always COMPLETED | worker lifecycle regression; live stop/restart |
| 2026-09-14 | `core/ui/worker.py`, `core/perception/visualizer.py`, `core/ui/main_window.py` | Developer HUD was always enabled and health values were constants | live UI captures and targeted tests |
| 2026-09-14 | `core/evidence/engine.py`, `core/perception/types.py`, `core/perception/pipeline.py` | Pixel distances were compared to normalized thresholds; absent tracks produced evidence | resolution, missing-object and empty-scene regressions |
| 2026-09-14 | `core/procedure/progress.py`, `core/procedure/evaluator.py`, `core/assurance/engine.py`, `core/assistance/recovery.py` | Future-step bypass, loose sequence/duration, and ungrounded recovery | 21 QA regressions plus component suite |
| 2026-09-14 | `core/mission/orchestrator.py` | Canonical headless Mission Orchestrator still selected legacy pose/hands directly | Orchestrator integration plus QA regressions pass with offscreen Qt |
