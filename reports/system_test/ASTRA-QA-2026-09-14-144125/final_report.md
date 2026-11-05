# ASTRA-EA System Validation Final Report

## Executive summary

The current working tree was audited, debugged, regression-tested, and exercised against a real camera. The software path is operational for local capture, MediaPipe pose/hands, UI rendering, local evidence/assurance logic, Ground Monitor reconnect, and bounded soak. The complete physical mission cannot be released because no operator-confirmed MAIN_BOX/RED_BOX/YELLOW_BOX action sequence was completed, and therefore the Golden Mission, physical interaction, recovery, and audible voice acceptance remain blocked.

## Automated tests

The host baseline passed **340/340** tests in 36.65 seconds. The sandbox baseline had **335 passed and 5 network failures** because socket creation was denied; the same five passed with host access. After fixes, the targeted QA/component set passed **93/93**, the final QA regression set passed **21/21**, and the camera-view matrix passed **12/12**. Python compilation passed. A post-fix full-suite rerun was attempted in the restricted sandbox and reproduced the five socket permission failures; host escalation was unavailable after the usage-limit review. `git diff --check` reports one pre-existing README trailing-space issue.

## Live camera and perception

Camera discovery found device 0 and device 1. Device 0 accepted 30/30 frames with 0 read failures at measured 26.1 FPS. The live perception run processed 1,800 frames in 60.03 seconds at 30.0 FPS; latency P50/P95/P99 was 14.68/18.22/21.86 ms. The two-minute Mission Console observer run captured 3,184 frames with 0 read failures and 3,182 UI-delivered frames (25.63 delivered FPS including UI actions). It observed 824 frames with 33 landmarks and 820 with hands. Accuracy was not evaluated against labeled ground truth. See `camera/`, `perception/`, and `performance/live_console_metrics.json`.

## Interaction, activity, procedure, assurance, recovery

Automated tests cover contact persistence, coupled motion, placement stabilization, release clearance, tri-state assurance, wrong object, skipped order, incomplete action, uncertainty, and closed-loop recovery. Live footage showed a person and hand/pose overlays but no controlled object procedure was confirmed. These components are **BLOCKED for physical acceptance**, not claimed successful from software fixtures.

## Mission Console, Ground Monitor, voice, storage

Mission Console remained responsive during resize, tab changes, overlay toggling, stop and restart. Its UI showed authoritative `STEP 01 / 04` and `Complete Step 01` guidance, and an uncertainty state when evidence was insufficient. Ground Monitor transitioned to `PARTIAL/OFFLINE` on controlled disconnect and back to `ONLINE/GOOD` on reconnect. Voice events were emitted through the local queue; audible hardware acceptance is blocked. SQLite initialized and storage remained writable. The observer captured raw camera evidence separately; this is not asserted as built-in mission recording proof.

## Performance and long run

The 10-second soak evaluated 299 frames at 29.88 FPS. RSS changed from 296.33 MB to 296.36 MB (+0.03 MB); verdict PASS and no leak detected. Live Console stage latency P50/P95/P99: capture 0.13/11.41/17.23 ms, detection 4.78/6.98/8.24 ms, pose 8.90/17.44/21.12 ms, hand 1.10/1.68/2.00 ms, tracking 0.01/0.02/0.03 ms, total 16.32/25.20/29.09 ms. CPU is available only through CPU PyTorch; no CUDA/GPU.

## Bugs found and fixed

Eight QA findings were fixed: confidence from zero visibility, legacy detector selection in both Mission Console and canonical Orchestrator, unsupported thread wait/cleanup status, always-on debug HUD and fake health telemetry, coordinate normalization, absent-object evidence, and procedure/assurance/recovery semantic bypasses. Each has regression coverage; details are in `change_log.md`.

## Release scorecard

| Component | Status |
|---|---|
| Automated regression | PASS — 340/340 baseline; 93/93 post-fix component; 21/21 QA; 25/25 final targeted integration |
| Camera | PASS |
| Pose | PASS — live 33-point observations |
| Hands | PASS — live observations |
| Objects / tracking | BLOCKED physical acceptance |
| Interaction / activity | BLOCKED physical acceptance |
| Procedure / assurance / recovery | PASS automated; BLOCKED physical Golden Mission |
| Mission Console / Ground | PASS observation |
| Voice | READY WITH LIMITATIONS — software path; audible check blocked |
| Evidence / storage | PASS software checks |
| Offline / failure handling | PASS automated and local reconnect observation |
| Long run / performance | PASS bounded soak; GPU unavailable |
| Golden Mission | BLOCKED |

## Final release status

**BLOCKED.** No unresolved critical software regression remains in the tested path, but release criteria require a human-confirmed physical Golden Mission, wrong-object deviation/recovery, and audible voice check. The system is suitable for continued ground validation and operator-assisted rehearsal; it is not flight-qualified or certified.

## Exact commands used

All commands, timestamps, working directories, exit codes and log paths are in `commands.jsonl`. Key commands were `python3 main.py --help`, `python3 main.py doctor`, `python3 main.py camera list`, `python3 main.py camera test --source 0 --frames 30`, `python3 main.py perception test --source 0 --frames 1800 --benchmark`, `pytest tests/ -v`, `python3 main.py benchmark soak --duration 10 --fps 30`, `python3 main.py config validate`, `python3 main.py experiment validate configs/experiments/demo.yaml`, `python3 main.py ml doctor`, and the live observer `python3 ../live_console.py`.
