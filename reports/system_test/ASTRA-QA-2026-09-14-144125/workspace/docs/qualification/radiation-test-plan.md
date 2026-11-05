# ASTRA-EA: Radiation Hardening & Effects Qualification Test Plan

**Document ID:** `ASTRA-QTP-RAD-001`  
**Test Identifier:** `QUAL-RAD-001` (TID) / `QUAL-RAD-002` (SEE/SEL)  
**Standard:** ECSS-E-ST-10-12C (Methods for the Calculation of Radiation Received and Its Effects) / ESCC 22900  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Target Environment:** LEO / ISS Radiation Environment (TID $50\text{ krad(Si)}$, Heavy Ion SEE LET up to $75\text{ MeV}\cdot\text{cm}^2/\text{mg}$)  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This qualification test plan outlines the radiation evaluation strategy for the ASTRA-EA compute platform, CMOS optical imager, and flash storage under high-energy ionizing and particle radiation.

Specific goals:
1. **Total Ionizing Dose (TID):** Expose powered and unpowered compute modules to Cobalt-60 gamma radiation up to $50\text{ krad(Si)}$ to verify threshold voltage stability, standby leakage current, and non-volatile memory retention.
2. **Single Event Effects (SEE):** Expose running compute modules to heavy ion beam lines to measure the cross-section of:
   - **Single Event Upset (SEU):** Bit-flips in DRAM, cache, or CPU register banks.
   - **Single Event Functional Interrupt (SEFI):** Peripheral interface hangs, PCIe bus resets, or camera frame loss.
   - **Single Event Latch-up (SEL):** Parasitic SCR turn-on causing high-current shorts. Verify zero destructive latch-up up to $\text{LET} = 75\text{ MeV}\cdot\text{cm}^2/\text{mg}$.

---

## 2. Test Facilities & Radiation Sources

### 2.1 TID Test Facility
- **Facility:** Certified Cobalt-60 ($\text{Co}^{60}$) gamma-ray irradiation chamber (ESCC 22900 compliant).
- **Dose Rate:** Low dose rate ($0.05 - 0.1\text{ rad(Si)/sec}$) to prevent dose-rate enhancement distortions.
- **Dosimetry:** Calibrated alanine pellets / thermoluminescent dosimeters (TLD) with $\pm 5\%$ accuracy.

### 2.2 Heavy-Ion SEE Facility
- **Facility:** Heavy-ion cyclotron / accelerator facility (e.g. UCL Louvain-la-Neuve or RADEF Jyväskylä).
- **Ion Cocktail:** High-LET ions covering $5$ to $75\text{ MeV}\cdot\text{cm}^2/\text{mg}$ (e.g. Carbon, Neon, Argon, Krypton, Xenon).
- **Beam Vacuum:** Target test chamber evacuated to $10^{-4}\text{ Torr}$ with remote positioning goniometer.

---

## 3. Radiation Software Defense Mechanisms

While physical shielding (aluminum equivalent $\ge 2.5\text{ mm}$) and rad-tolerant components provide primary defense, ASTRA-EA implements multi-layered software-level resilience:

```text
RADIATION DEFENSE LAYER:
├── 1. Memory Level:
│   ├── Kernel ECC single-bit error correction & double-bit error detection (EDAC)
│   └── Memory scrubbing thread scanning critical procedure state registers
├── 2. Model Level:
│   ├── Periodic runtime SHA-256 verification of in-memory ONNX weight arrays
│   └── Automatic fallback to ColorHeuristicDetector if weight corruption detected
├── 3. Process Level:
│   ├── Hardware watchdog timer reset via high-priority heartbeat thread
│   └── Subsystem crash isolation (ProcessGuard auto-restarts failed inference worker)
└── 4. State Level:
    ├── Microsecond SQLite WAL transaction journal preserving state history
    └── Unalterable causal evidence chain stored on wear-leveled flash
```

> [!WARNING]
> **Engineering Boundary:** Software defenses mitigate transient upsets and soft errors, but **cannot prevent hardware-level destructive latch-up or permanent dielectric breakdown**. Physical radiation qualification remains mandatory.

---

## 4. Test Procedure & In-Beam Monitoring

1. **Pre-Irradiation Characterization:**
   - Execute full functional sweep `SFB-001`. Record quiescent current $I_{DDQ}$, boot time, FPS, and model hash.
2. **In-Beam Irradiation:**
   - Mount de-lidded or thinned chip sample in beam line.
   - Connect high-speed latch-up power protection circuit (fast-crowbar with $<10\ \mu\text{s}$ shutdown response if $I > 1.5 \times I_{nom}$).
   - Stream live camera video through detection pipeline while ion beam is active.
   - Record: Fluence ($\text{ions}/\text{cm}^2$), SEU bit-flip count, SEFI watchdog resets, SEL trips.
3. **Step-Dose Functional Checks:**
   - At 10 krad, 25 krad, 40 krad, and 50 krad milestones, pause beam and execute full procedure verification check.
4. **Post-Radiation Annealing:**
   - 24-hour room temperature anneal followed by 168-hour accelerated aging at $+100^\circ\text{C}$ to test for rebound effects.

---

## 5. Acceptance Criteria

- **TID Tolerance:** Functional execution preserved up to $50\text{ krad(Si)}$ with supply current increase $<25\%$.
- **SEL Immunity:** No destructive latch-up events observed up to $\text{LET} = 75\text{ MeV}\cdot\text{cm}^2/\text{mg}$.
- **SEU Recovery:** When an SEU bit-flip occurs in inference memory, software watchdog restarts the inference worker in $\le 2.0$ seconds without loss of procedural progress.
- **Model Checksum:** Model weights on disk remain 100% bit-identical post-radiation.
