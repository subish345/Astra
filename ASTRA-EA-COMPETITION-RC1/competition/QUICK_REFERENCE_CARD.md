# ASTRA-EA: Operator Quick Reference Card

**Printable 1-Page Field Card for Demonstration Operators**

---

## 11-Step Flight Demonstration Checklist

```
 [ ] 1. CONNECT CAMERA      Plug in USB 3.0 webcam; position 50 cm overhead.
 [ ] 2. RUN FINAL-CHECK     Execute: astra competition-check (Verify all PASS).
 [ ] 3. START DEMO          Execute: astra demo (Console at :8000, Ground at :8080).
 [ ] 4. CONFIRM READY       Verify browser displays green/cyan "READY" status.
 [ ] 5. START EXPERIMENT    Click "BEGIN EXPERIMENT" button on console.
 [ ] 6. FOLLOW PROCEDURE    Perform Step 1: Grasp Specimen Tube.
 [ ] 7. OBSERVE STATUS      Confirm console transitions to "STEP 1 VERIFIED".
 [ ] 8. DEMO DEVIATION      Perform Step 2 Error: Grasp Centrifuge Tube instead of Pipette.
                            Verify Voice: "Incorrect object selected" & Alert Banner.
 [ ] 9. DEMO RECOVERY       Replace tube and grasp Pipette.
                            Verify console: "RECOVERY VERIFIED".
 [ ] 10. COMPLETE RUN       Complete Steps 3 & 4. Verify "MISSION COMPLETED".
 [ ] 11. AUDIT REPORT       Open Evidence Drawer and review final mission report.
```

---

## Emergency Troubleshooting Matrix

| Symptom | Rapid Diagnosis | Immediate Action |
| :--- | :--- | :--- |
| **No Camera Feed** | Camera device node changed | Run `astra final-check`. Relaunch with `astra demo --camera 0` or `--camera 1`. |
| **Voice Audio Muted** | Pulseaudio / ALSA error | Check system volume; if headless, system safely auto-defaults to visual guidance. |
| **Step Not Verifying** | Tool occluded by hand/body | Shift grip to ensure tool is visibly exposed to overhead camera. |
| **Browser Console Lag** | Multiple heavy browser tabs | Refresh page (`Ctrl+F5`) or close background tabs. Core runtime is unaffected. |
| **Need Clean Restart** | Inadvertent sequence error | Press `Ctrl+C` in terminal, then rerun `astra demo`. State resets in $<3$ seconds. |

---

## Authoritative System Claim Boundary (Memorize)

> *"ASTRA-EA is an engineering-grade ground demonstrator (TRL 4) validating offline, edge-native experiment assurance. It is not flight-qualified or zero-gravity certified."*
