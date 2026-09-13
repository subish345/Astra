# Anomaly Playbook: Model Inference Failure

**Anomaly Code:** `ANOM_MOD_002`  
**Classification:** `MODEL`  
**Severity:** `WARNING` / `CRITICAL`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- ONNX Runtime throws runtime exception or CUDA/NPU kernel memory error during `run()`.
- Inference latency spikes above critical margin (>500 ms).
- Detector returns corrupted bounding boxes or empty tensor.

## 2. Immediate Safe Autonomous Response (Section 30)
1. Exception caught by perception guard; system prevents crash.
2. System engages validated fallback detector (Color/Spatial baseline detector).
3. If fallback is unavailable: Experiment transitions to `PAUSED`.

## 3. Operator Actions
1. **Acknowledge Alert:** Acknowledge `MODEL_FAILED` warning on HUD.
2. **Review Fallback State:** Confirm whether fallback detector is actively tracking basic apparatus colors.
3. **Escalation:** If primary model cannot be reloaded, abort run or switch to manual ground observation.

## 4. Evidence to Capture
- Tensor input shape and exception traceback in `flight_data/diagnostics/flight.log`.
- Current silicon memory RSS usage.
