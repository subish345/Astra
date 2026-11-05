# ASTRA-EA: Live Demonstration Troubleshooting Playbook

**Strict Demo Policy:** **NEVER MODIFY SOURCE CODE DURING A JUDGE DEMONSTRATION.**  
All recoveries must use pre-validated CLI switches, hardware reconnections, or clean restart sequences.

---

## 1. Camera Failure Playbook

### Symptoms
- Mission Console displays black video viewport or `CAMERA BLACKOUT / INGESTION TIMEOUT`.
- Terminal logs `[ERROR] V4L2 device timeout` or `cv2.VideoCapture read() returned None`.

### Recovery Actions (Estimated Time: 10 seconds)
1. **Check Hardware Connection:** Firmly reseat the USB 3.0 webcam cable.
2. **Device Discovery:** In a spare terminal, run:
   ```bash
   astra final-check
   ```
3. **Switch Camera Index:** If the kernel shifted `/dev/video0` to `/dev/video1` or `/dev/video2`, restart the demo with an explicit index:
   ```bash
   astra demo --camera 1
   ```
4. **Synthetic Video Fallback:** If the physical camera hardware is physically damaged, switch to the simulated video pipeline:
   ```bash
   astra demo --simulated-camera
   ```

---

## 2. Model Inference Exception Playbook

### Symptoms
- Terminal logs PyTorch CUDA OOM (Out Of Memory) or model forward pass crash.
- Mission Console indicates `PERCEPTION DEGRADED`.

### Recovery Actions (Estimated Time: 5 seconds)
1. Do not attempt to debug or re-compile neural weights.
2. Immediately launch with the secondary rule-based baseline detector:
   ```bash
   astra demo --fallback-baseline
   ```
3. **Judge Explanation:** *"Notice our fault-isolated architecture: when the deep neural engine experiences compute exhaustion, the runtime gracefully falls back to the deterministic color-heuristic detector so mission assurance continues without halting."*

---

## 3. Mission Console / Browser Freeze Playbook

### Symptoms
- Browser tab stops updating frames or WebSocket indicator shows `DISCONNECTED`.
- The terminal indicates the core runtime is still logging at 34 FPS.

### Recovery Actions (Estimated Time: 3 seconds)
1. The onboard core runtime is decoupled from the web UI; a frozen browser has **zero impact** on procedural assurance or video recording.
2. Force-refresh the browser tab:
   ```
   Ctrl + Shift + R  (or F5)
   ```
3. If Chrome/Firefox hung, open a fresh tab to:
   ```
   http://127.0.0.1:8000
   ```
   The WebSocket will immediately re-attach to the live mission state.

---

## 4. Audio / Voice Output Muted

### Symptoms
- Voice guidance does not speak during deviation; terminal prints `ALSA lib pcm.c: Unknown PCM default`.

### Recovery Actions (Estimated Time: 2 seconds)
1. Check workstation hardware volume and headphone jack connection.
2. The system is designed with an automated visual guidance fallback:
   - All voice strings are rendered in high-contrast text directly across the Mission Console HUD.
3. **Judge Explanation:** *"Our cockpit UX follows aerospace multi-modal redundancy: when cabin acoustic channels are degraded or muted, the visual guidance heads-up display automatically assumes primary alert priority."*

---

## 5. Clean Demo Reset Sequence

If an accidental sequence of physical mistakes necessitates restarting the demonstration from scratch:
1. Press `Ctrl + C` in the demo terminal.
2. Wait 2 seconds for clean background worker termination.
3. Re-launch:
   ```bash
   astra demo
   ```
4. Refresh browser: `http://localhost:8000`. The experiment is reset to Step 1 in $<5$ seconds.
