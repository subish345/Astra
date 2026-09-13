# ASTRA-EA: Nonconformance Reporting (NCR) & Corrective Action Procedure

**Document ID:** `ASTRA-SOP-NCR-001`  
**Classification:** Spacecraft Quality Assurance & Qualification Standard Operating Procedure  
**Standard Adherence:** ECSS-Q-ST-10-09C (Nonconformance Control System) / NASA-STD-8739.8  
**Governing Baseline:** `ASTRA-EA-QB-001`  

---

## 1. Purpose & Core Policy

This procedure defines the mandatory process for documenting, classifying, investigating, and closing engineering nonconformances that occur during qualification testing.

> [!CRITICAL]
> **No Erasure Policy:**  
> A failed test or anomalous observation shall **NEVER be deleted, overwritten, or omitted** from the qualification record. Every anomaly must generate a formal Nonconformance Record (NCR). A qualification test can only be marked completed after the associated NCR has been formally dispositioned and closed via successful retest.

---

## 2. Nonconformance Severity Classification

Every NCR is assigned one of four formal severity levels:

| Severity | Definition | Examples | Authority Required |
| :--- | :--- | :--- | :--- |
| **`CRITICAL`** | Permanent hardware damage, structural cracking, loss of containment, unrecoverable data corruption, or complete loss of procedural assurance. | Dielectric breakdown under vacuum, optical lens fracture during vibration, destructive latch-up. | Material Review Board (MRB) + Program Manager |
| **`HIGH`** | Requirement violation that compromises operational mission performance without physical destruction. | Pipeline FPS drops below 30.0 under thermal load, thermal throttling triggered at $+50^\circ\text{C}$, cold-boot $>5.0$s. | Systems Engineering Lead + MRB |
| **`MEDIUM`** | Transient anomaly with self-recovery or minor performance margin reduction that does not breach primary requirements. | Minor auto-exposure oscillation below 60 Lux, transient socket backpressure on slow network clients. | Subsystem Lead |
| **`LOW`** | Minor documentation discrepancy, non-critical telemetry jitter, or superficial mechanical blemish. | Non-affecting cosmetic scratch on bracket, minor telemetry timestamp formatting anomaly. | Test Engineer |

---

## 3. Nonconformance Lifecycle & Status Vocabulary

```text
[ANOMALY OCCURS]
       │
       ▼
     OPEN ──> ANALYZING ──> CORRECTIVE_ACTION ──> RETEST ──> CLOSED
       │                                                        ▲
       └──────────────────── WAIVED (MRB Disposition) ──────────┘
```

- **`OPEN`**: Anomaly recorded; immediate test containment executed.
- **`ANALYZING`**: Root Cause Analysis (RCA) in progress (e.g. 5-Whys, Fishbone, Fault Tree).
- **`CORRECTIVE_ACTION`**: Engineering modification formulated; Change Impact Analysis completed.
- **`RETEST`**: Re-executing failed qualification test with modified hardware/software.
- **`CLOSED`**: Retest passed; verification evidence verified; formally accepted.
- **`WAIVED`**: Formal waiver approved by MRB (e.g. specialized aerospace shaker table test waived for ground demonstrator phase, scheduled for facility test).

---

## 4. Nonconformance Record Schema

Every NCR is serialized in `qualification/nonconformance/NCR-xxx.json`:

```json
{
  "ncr_id": "NCR-THM-001",
  "qualification_build_id": "ASTRA-EA-QB-001",
  "test_id": "QUAL-THM-001",
  "requirement_id": "ASTRA-ENV-004",
  "severity": "HIGH",
  "date_opened": "2026-09-13T14:30:00Z",
  "originator": "Test Operations Lead",
  "failure_description": "At +50°C ambient, CPU core frequency throttled from 1.8 GHz to 1.1 GHz after 45 minutes of continuous inference, dropping pipeline FPS to 24.1.",
  "root_cause": "Thermal interface material (TIM) between compute module and test fixture had void bubbles, increasing junction-to-case thermal resistance from 1.2 K/W to 2.8 K/W.",
  "corrective_action": "Replaced paste with aerospace-grade pre-cut thermal foil (CHO-THERM). Re-torqued mounting plate to 4.5 N*m.",
  "impact_analysis": {
    "affected_subsystems": ["THERMAL", "PERFORMANCE", "OPTIMIZATION"],
    "affected_tests": ["QUAL-THM-001", "QUAL-TVAC-001"],
    "software_change_required": false
  },
  "retest_id": "QUAL-THM-001-R1",
  "disposition": "CORRECT_AND_RETEST",
  "date_closed": "2026-09-13T17:00:00Z",
  "status": "CLOSED"
}
```

---

## 5. Nonconformance Registry in ASTRA-EA

Historical and active NCR records are stored in `qualification/nonconformance/` and audited via the unified CLI:

```bash
astra qualification nonconformances
```
