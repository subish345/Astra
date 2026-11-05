# ASTRA-EA: Spacecraft Payload Cybersecurity Threat Model & Defense-in-Depth

**Classification:** Payload Cyber-Resilience & Threat Assessment  
**Document ID:** `ASTRA-SEC-001`  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Security Boundary Architecture

ASTRA-EA enforces four concentric defense zones:

```
[ZONE 4: EXTERNAL NETWORK / INTERNET]  <=== AIR-GAP (Zero physical connection)
                  |
                  v
[ZONE 3: GROUND STATION NETWORK]       <=== Authenticated ground monitoring interface
                  |
                  v
[ZONE 2: VEHICLE DATA BUS / LAN]       <=== Read-only telemetry downlink; schema-validated commands
                  |
                  v
[ZONE 1: ONBOARD AIR-GAPPED CORE]      <=== POSIX local loopback; isolated memory; local SQLite
```

---

## 2. Threat Vector Identification & Mitigation Matrix

| Threat Vector | Attack Scenario | Potential Impact | ASTRA-EA Mitigation Mechanism | Residual Risk |
| :--- | :--- | :--- | :--- | :---: |
| **T-01: Unauthorized Ground Connection** | Rogue client connects to Ground Monitor port | Eavesdropping on crew video | IP whitelisting + read-only WebSocket feeds | **LOW** |
| **T-02: Malformed Network Message** | Fuzzed JSON sent over telemetry socket | Service crash (DoS) | Strict Pydantic schema validation; invalid packets dropped | **LOW** |
| **T-03: Corrupted / Trojaned Model** | Tampered neural weights loaded on boot | False verification of dangerous actions | Mandatory SHA-256 integrity hash check prior to loading | **NEGLIGIBLE** |
| **T-04: Modified Configuration File** | Tampered thresholds allowing false passes | Undetected procedural deviation | YAML strict schema validator + hash verification on startup | **NEGLIGIBLE** |
| **T-05: Malicious Experiment Procedure**| Arbitrary code injection via YAML | Privilege escalation | Procedures are pure declarative data; zero eval() or code execution | **NEGLIGIBLE** |
| **T-06: Storage Tampering** | Post-mission modification of mission logs | Falsified science verification | SQLite WAL mode + microsecond hash-chained event logs | **LOW** |
| **T-07: Replay Attack** | Replay of old `STEP_VERIFIED` telemetry | False ground operator situational awareness | Monotonic sequence counter + microsecond UTC SCET timestamps | **LOW** |
| **T-08: Compromised Software Update** | Upload of unvalidated software binary | System instability / loss of assurance | Cryptographic package signing + dual-slot A/B rollback mechanism | **LOW** |

---

## 3. Model & Configuration Integrity Enforcement
1. **Startup Check:** Prior to initializing the neural runtime, `core/cli/commands.py` verifies the model checkpoint against `competition/CHECKSUMS/SHA256SUMS`.
2. **Mismatch Action:** If a hash mismatch or corrupted weight matrix is detected, the loader immediately aborts initialization, flags `MODEL_INTEGRITY_VIOLATION`, and fails over to the baseline color heuristic detector.

---

## 4. Software Update & Rollback Architecture

For future orbital payload maintenance:
$$\text{Signed Update Package} \longrightarrow \text{Staging Partition B} \longrightarrow \text{Integrity Audit} \longrightarrow \text{Dry-Run Self-Test} \longrightarrow \text{Activate}$$
- **Atomic Rollback:** If the new version encounters an unhandled exception or watchdog timeout during the first 3 runs, the bootloader automatically reverts to the previous validated partition (Slot A) without manual ground intervention.
