# Anomaly Playbook: Storage Capacity Degradation

**Anomaly Code:** `ANOM_STR_003`  
**Classification:** `STORAGE`  
**Severity:** `WARNING` (>85%) / `CRITICAL` (>95%)  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Storage partition usage exceeds 85% capacity threshold.
- `StorageManager` flags partition health as `WARNING` or `CRITICAL`.
- Console status badge changes to `DEGRADED`.

## 2. Immediate Safe Autonomous Response (Section 28)
1. System triggers Section 28 priority retention pruning:
   - Debug logs purged first.
   - Diagnostic logs truncated.
   - Low-priority video segments pruned.
2. **Absolute Rule:** Mission events, assurance decisions, and cryptographic evidence are **never deleted**.

## 3. Operator Actions
1. **Acknowledge Alert:** Acknowledge storage headroom warning.
2. **Execute Export:** Trigger `astra mission export` on completed runs to transfer archive data off primary partition.
3. **Escalation:** If storage exceeds 95%, pause video recording while keeping event telemetry active.

## 4. Evidence to Capture
- Output of `StorageManager.get_usage()`.
- Disk usage summary across partitions.
