# ASTRA-EA Findings-Driven Hardening Operational Guide (Phase 21, D21.17)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Hardening Philosophy & Guiding Rules

In accordance with Phase 21 Section 1:

> **"We found a real problem, reproduced it, identified why it happened, fixed the correct layer, proved the fix, and proved that the fix did not break anything else."**

### Non-Negotiable Hardening Invariants
1. **Never Invent Defects**: Hardening is driven solely by empirical data observed during operational rehearsals or testing.
2. **Never Weaken Assurance**: Validated procedure rules, detection confidence thresholds, and deterministic state machines must NEVER be degraded simply to make a demonstration easier.
3. **No Fix Without Reproduction**: Every CRITICAL and HIGH severity finding must have a reproducible test case before permanent sign-off.
4. **No Cascading Untested Changes**: Every modification is isolated, traced to root cause, and verified with a dedicated regression test.

---

## 2. The Hardening Lifecycle Loop

```text
OBSERVE (Empirical finding during operational rehearsal or HIL drill)
   ↓
REPRODUCE (Create automated test reproducing the exact failure mode)
   ↓
ANALYZE (Conduct 5-Why, Timeline, or Trace Root Cause Analysis)
   ↓
FIX (Apply minimal, targeted corrective action at the correct layer)
   ↓
VERIFY (Confirm reproduction test now passes cleanly)
   ↓
REGRESS (Run dedicated regression suite to prove zero unintended side effects)
   ↓
REHEARSE (Re-run Golden Mission and Dress Rehearsal end-to-end)
   ↓
RELEASE (Mint new Release Candidate with formal audit documentation)
```

---

## 3. Hardening CLI Command Reference

### Inspect All Registered Findings
```bash
astra hardening findings
```

### Deep-Dive Analysis of Root Cause and CAPA
```bash
astra hardening analyze FINDING-001
```

### Reproduce a Specific Finding via Automated Regression
```bash
astra hardening reproduce FINDING-001
```

### Run Full Regression Suite and Domain Workflows
```bash
astra hardening regression
```

### Generate Standalone Audit HTML Reports
```bash
astra hardening report
```
Generates the following reports in `reports/hardening/`:
* `reports/hardening/findings.html`
* `reports/hardening/root_causes.html`
* `reports/hardening/corrective_actions.html`
* `reports/hardening/regression.html`
* `reports/hardening/rc_comparison.html`
* `reports/hardening/final_hardening_report.html`

### Evaluate Release Candidate Readiness Gate
```bash
astra hardening readiness
```

---

## 4. Release Candidate 2 (RC2) Baseline

* **Product Version**: `ASTRA-EA-v1.0`
* **Software Version**: `1.0.0-RC2`
* **Build Target**: `deployment/flight/ASTRA-EA-v1.0.0-RC2/`
* **Open Critical Findings**: `0`
* **Open High Findings**: `0`
* **Regression Status**: `PASS (326 / 326 tests)`
* **Readiness Verdict**: **`READY`**
