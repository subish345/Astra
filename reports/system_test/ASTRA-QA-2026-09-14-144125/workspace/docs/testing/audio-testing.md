# ASTRA-EA — Audio Testing Strategy

## Verification for Offline Voice Assistance Subsystem

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Objectives

Verify that speech synthesis:
1. Prioritizes critical alerts ahead of routine guidance.
2. Deduplicates identical messages within configured cooldown intervals.
3. Operates offline without external network dependencies.
4. Survives audio hardware dropouts without crashing the application.

---

## 2. Test Suites Overview

[`tests/audio/test_voice_architecture.py`](file:///home/subish-loq/Documents/astra/tests/audio/test_voice_architecture.py) verifies:
- `test_audio_deduplicator_cooldown`: Suppresses immediate duplicate calls within cooldown.
- `test_audio_queue_manager_priorities_and_preemption`: Confirms `CRITICAL` priority interrupts pending speech and purges lower-priority queue items.
- `test_audio_manager_failing_provider_resilience`: Verifies hardware audio exceptions are logged without propagating errors to callers.
- `test_offline_tts_provider_headless_mode`: Verifies simulation mode when no physical sound device is present.

---

## 3. Operational CLI Test

Run live voice testing:
```bash
python3 main.py voice test
```

Expected output:
```text
============================================================
 ASTRA-EA LOCAL VOICE SUBSYSTEM TEST
============================================================
Provider:  OfflineTTSProvider (pyttsx3 air-gapped speech synthesis)
Queue:     Priority preemption & cooldown deduplication enabled
------------------------------------------------------------
[INFO    ] Synthesizing: "ASTRA-EA voice guidance channel initialized. Systems nominal."
[GUIDANCE] Synthesizing: "Step 2 active: Grasp the red specimen container."
[WARNING ] Synthesizing: "Warning: Yellow box detected instead of red specimen container."
[DEDUP   ] Immediate duplicate rejected: True (Allowed: False)
[CRITICAL] Synthesizing: "Critical procedure deviation detected. Return yellow box immediately."
[✓] Voice subsystem test complete.
============================================================
```
