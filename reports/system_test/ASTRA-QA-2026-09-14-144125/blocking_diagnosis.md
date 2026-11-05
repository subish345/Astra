# Blocking Diagnosis

## Reproduction

`python3 main.py system-test` returned exit code 0 and reported:

```text
Automated Verification Sequence:  [PASS]
Optical Sensor (/dev/video0):       [MANUAL TEST REQUIRED]
Physical Hand-Object Coupling:     [MANUAL TEST REQUIRED]
Real Wrong-Object Distractor:      [MANUAL TEST REQUIRED]
Astronaut Physical Recovery:        [MANUAL TEST REQUIRED]
```

`python3 main.py final-check` returned `READY FOR DEMONSTRATION`. `python3 main.py demo --headless` completed successfully, but that path intentionally builds synthetic NumPy frames and is a simulation; it cannot clear the physical hardware gate.

## Root cause

The `system-test` command is designed to leave camera interaction, hand-object coupling, wrong-object deviation, and recovery as human-in-the-loop checks. The checklist at `reports/testing/manual_camera_checklist.md` still has no operator sign-off. The QA release status is therefore **BLOCKED by missing physical acceptance evidence**, rather than by an automated software failure.

The real camera was previously opened successfully (30/30 frames, 26.1 FPS; zero read failures), and the Mission Console observed 33-point pose and hands. That proves camera/perception startup only. It does not prove the four-step object procedure.

## Required action to clear the gate

Run `python3 main.py demo --source 0 --procedure configs/experiments/demo.yaml` with the physical MAIN_BOX, RED_BOX, YELLOW_BOX and work surface. Record PASS/FAIL for camera, pose, hands, each object, approach, grasp, move, place, release, wrong-object deviation, recovery, uncertainty, voice, and mission completion in `reports/testing/manual_camera_checklist.md`, then rerun `python3 main.py system-test`.
