# Final Test Matrix

| Component | Test | Expected | Observed | Status | Evidence |
|---|---|---|---|---|---|
| Camera | 30 real frames | no read failures | 30/30, 26.1 FPS | PASS | `camera/test_host.log` |
| Pose | live 33 landmarks | real landmarks | 824 frames | PASS | `perception/state_*.json` |
| Hands | live hands | anatomical observations | 820 frames | PASS | `performance/live_console_metrics.json` |
| Objects | physical boxes | labels/tracks | no controlled box run | BLOCKED | `manual_camera_checklist.md` |
| Tracking | persistent IDs | stable lifecycle | automated pass; physical blocked | BLOCKED | `regression/complete_components.log` |
| Interaction | grasp/place/release | evidence-gated | automated only | BLOCKED | `tests/regression/test_qa6_runtime_safety.py` |
| Activity | configured actions | tri-state | automated only | BLOCKED | component JUnit |
| Procedure | four ordered steps | no bypass | automated pass; physical blocked | BLOCKED | `automated/cli_experiment.log` |
| Assurance | correct/wrong/uncertain | tri-state | automated pass | PASS | component JUnit |
| Recovery | observed corrective action | closed loop | automated pass | PASS | component JUnit |
| UI | resize/tabs/overlays/stop | responsive | observed | PASS | `mission_console/*.png` |
| Voice | queue/cooldown | no per-frame spam | 2 voice events | LIMITED | `mission_console/live_events.jsonl` |
| Storage | DB/evidence | readable/persistent | doctor and tests pass | PASS | `automated/doctor.log` |
| Ground | disconnect/reconnect | reconcile | PARTIAL → ONLINE | PASS | `mission_console/live_events.jsonl` |
| Offline | local processing | no cloud dependency | offline mode; CPU | PASS | `environment.json` |
| Performance | soak | bounded memory | 29.88 FPS, +0.03 MB | PASS | `performance/soak_10s.log` |
| Golden Mission | complete physical run | all four steps | not performed/confirmed | BLOCKED | `manual_camera_checklist.md` |
