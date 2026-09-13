# Anomaly Playbook: Offline Audio Voice Guidance Failure

**Anomaly Code:** `ANOM_VOI_005`  
**Classification:** `VOICE`  
**Severity:** `NOTICE`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Offline TTS engine fails to initialize audio output device (ALSA/PulseAudio).
- Audio speech synthesis thread throws exception or audio buffer underruns.

## 2. Immediate Safe Autonomous Response
1. Voice manager logs degradation.
2. System continues running; cognitive visual prompts on the Mission Console HUD take full operational precedence.
3. Assurance verification logic is completely unaffected.

## 3. Operator Actions
1. Confirm visual instructions on the touch display HUD.
2. Verify headset volume and physical audio jack / Bluetooth link.
3. Run audio test CLI during post-mission maintenance:
   ```bash
   astra voice test
   ```

## 4. Evidence to Capture
- Audio queue backlog depth and audio exception log in `flight_data/diagnostics/flight.log`.
