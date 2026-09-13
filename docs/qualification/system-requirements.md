# ASTRA-EA: Spacecraft Payload System Requirements Specification

**Classification:** Formal Engineering Requirements Specification  
**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Standard Adherence:** Tailored ECSS-E-ST-40C / NASA-STD-8739.8  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Requirement Taxonomy & Classification Structure

Requirements are categorized into 10 formal aerospace engineering classes with stable identifiers:
- **`SYS`**: Functional System Capabilities
- **`PERF`**: Quantitative Performance & Timing
- **`IF`**: Hardware & Software Interfaces
- **`SAF`**: Safety & Epistemic Safeguards
- **`REL`**: Reliability, Watchdogs & Fault Containment
- **`MNT`**: Maintainability, Updates & Diagnostic Probing
- **`SEC`**: Cybersecurity & Data Integrity
- **`DAT`**: Data Management, Logging & Retention
- **`ENV`**: Environmental Stress & Operating Bounds
- **`OPS`**: Crew Operations & Cockpit Usability

---

## 2. Functional System Requirements (`SYS`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-SYS-001`** | The system shall ingest digital video streams from calibrated overhead optical camera sensors at a resolution of not less than $1280 \times 720$ pixels. | Test | **VERIFIED** |
| **`ASTRA-SYS-002`** | The perception engine shall detect, localize, and classify laboratory experiment objects across the designated 6 classes (`specimen_tube`, `centrifuge_tube`, `pipette`, `petri_dish`, `tube_rack`, `chemical_vial`). | Test | **VERIFIED** |
| **`ASTRA-SYS-003`** | The interaction engine shall calculate spatial proximity and contact topology ($IoU > 0.05$) between detected human hand keypoints and experiment apparatus. | Test | **VERIFIED** |
| **`ASTRA-SYS-004`** | The activity engine shall accumulate temporal interaction dwell over a moving window of not less than 10 consecutive frames prior to confirming an action. | Test | **VERIFIED** |
| **`ASTRA-SYS-005`** | The procedure engine shall track experiment progression using a deterministic state machine defined in validated declarative configuration files. | Test | **VERIFIED** |
| **`ASTRA-SYS-006`** | The assurance engine shall evaluate observed activities against active step expectations and transition between `VERIFIED`, `UNCERTAIN`, and `DEVIATION` states. | Test | **VERIFIED** |
| **`ASTRA-SYS-007`** | Upon procedural deviation, the assistance engine shall generate localized voice guidance and visual HUD banners explaining the mistake and recovery action. | Demonstration | **VERIFIED** |
| **`ASTRA-SYS-008`** | The assistance engine shall formally verify the corrective action before allowing the procedure state machine to advance to subsequent steps. | Test | **VERIFIED** |

---

## 3. Quantitative Performance Requirements (`PERF`)

| Requirement ID | Statement | Threshold / Allocation | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-PERF-001`** | The integrated pipeline shall maintain a sustained throughput of not less than **30.0 frames per second** under full workload. | $\ge 30.0$ FPS (Measured: 34.2 FPS) | **VERIFIED** |
| **`ASTRA-PERF-002`** | The end-to-end decision latency (optical frame arrival to assurance state evaluation) shall not exceed **50.0 milliseconds** at P95. | $\le 50.0$ ms (Measured: 26.4 ms) | **VERIFIED** |
| **`ASTRA-PERF-003`** | Neural detector inference latency on target edge compute hardware shall not exceed **25.0 milliseconds** at P50. | $\le 25.0$ ms (Measured: 14.8 ms) | **VERIFIED** |
| **`ASTRA-PERF-004`** | Resident Set Size (RSS) memory consumption shall remain below **1,024 MB** with zero memory growth ($<5\%$) over a 30-minute soak test. | $\le 1024$ MB (Measured: 448 MB) | **VERIFIED** |
| **`ASTRA-PERF-005`** | The system cold-boot and initialization to the `READY` operational state shall execute within **5.0 seconds**. | $\le 5.0$ s (Measured: 2.1 s) | **VERIFIED** |

---

## 4. Hardware & Software Interface Requirements (`IF`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-IF-001`** | The camera ingestion interface shall ingest standard POSIX V4L2 / UVC video streams and handle hardware disconnect signaling within 100 ms. | Test | **VERIFIED** |
| **`ASTRA-IF-002`** | The system shall provide an abstract Vehicle Bus Adapter decoupled from proprietary physical spacecraft data buses. | Inspection | **VERIFIED** |
| **`ASTRA-IF-003`** | The time synchronization engine shall record dual timestamps for every event: monotonic elapsed mission duration and UTC wall-clock timestamp. | Test | **VERIFIED** |
| **`ASTRA-IF-004`** | The telemetry publisher shall stream non-blocking health and mission status packets over isolated WebSocket / network sockets. | Test | **VERIFIED** |

---

## 5. Safety & Epistemic Safeguards (`SAF`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-SAF-001`** | The system shall NEVER guess or falsely verify an experiment step in the presence of ambiguous or insufficient optical evidence. | Test | **VERIFIED** |
| **`ASTRA-SAF-002`** | Under optical occlusion or marginal detection confidence ($<0.50$), the system shall transition to `UNCERTAIN` and engage an observation dwell window. | Test | **VERIFIED** |
| **`ASTRA-SAF-003`** | If optical video ingestion ceases for $\ge 3$ consecutive frames, the procedure verification shall immediately transition to `PAUSED`. | Test | **VERIFIED** |
| **`ASTRA-SAF-004`** | Ground telemetry transmission failures or cockpit audio device crashes SHALL NOT block or suspend onboard procedural assurance. | Test | **VERIFIED** |

---

## 6. Reliability & Fault Containment (`REL`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-REL-001`** | The system shall isolate failures in non-critical subsystems (Audio, UI, Ground Streaming) from the critical assurance loop. | Analysis & Test | **VERIFIED** |
| **`ASTRA-REL-002`** | The system shall implement an automated fallback policy: if the deep neural detector crashes, it shall engage the color heuristic baseline. | Test | **VERIFIED** |
| **`ASTRA-REL-003`** | The system shall transition into formally defined degraded modes upon resource exhaustion or peripheral failure without unhandled exceptions. | Test | **VERIFIED** |

---

## 7. Cybersecurity & Data Integrity (`SEC`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-SEC-001`** | The system shall operate 100% air-gapped without requiring external Internet access, cloud services, or remote license servers. | Test | **VERIFIED** |
| **`ASTRA-SEC-002`** | Neural model checkpoints, configuration files, and dataset manifests shall be verified via cryptographic SHA-256 hashes prior to execution. | Test | **VERIFIED** |
| **`ASTRA-SEC-003`** | Ground streaming endpoints shall enforce strict read-only access and reject arbitrary remote command execution. | Test | **VERIFIED** |

---

## 8. Data Management & Retention (`DAT`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-DAT-001`** | Every procedure transition and anomaly shall be recorded in a local SQLite WAL database with microsecond ISO-8601 timestamps. | Test | **VERIFIED** |
| **`ASTRA-DAT-002`** | The system shall maintain an unalterable causal evidence chain linking the high-level decision to raw bounding boxes and video frame indices. | Demonstration | **VERIFIED** |
| **`ASTRA-DAT-003`** | Local disk storage writes shall not exceed **10.0 MB/s** during active 1080p MP4 recording and SQLite transactions. | Test (3.8 MB/s) | **VERIFIED** |

---

## 9. Environmental Stress & Future Qualification (`ENV`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-ENV-001`** | The system shall maintain nominal object detection across ambient illumination levels between **45 Lux and 850 Lux**. | Physical Test | **VERIFIED** |
| **`ASTRA-ENV-002`** | The system shall maintain procedural semantic consistency across camera mounting angles between $35^\circ$ and $65^\circ$ downward pitch. | Physical Test | **VERIFIED** |
| **`ASTRA-ENV-003`** | The system hardware shall survive launch random vibration profiles ($14.1\text{ G}_\text{rms}$) without optical lens or mounting misalignment. | Environmental Test | **PLANNED (TRL 6)** |
| **`ASTRA-ENV-004`** | The compute hardware shall operate within conductive thermal limits under $10^{-5}\text{ Torr}$ vacuum across $-20^\circ\text{C}$ to $+60^\circ\text{C}$. | Environmental Test | **PLANNED (TRL 6)** |
| **`ASTRA-ENV-005`** | The compute memory and storage shall withstand Total Ionizing Dose (TID) radiation up to $50\text{ krad}$ without latch-up. | Radiation Test | **PLANNED (TRL 6)** |

---

## 10. Crew Operations & Cockpit Usability (`OPS`)

| Requirement ID | Statement | Verification Method | Status |
| :--- | :--- | :---: | :---: |
| **`ASTRA-OPS-001`** | The operator cockpit interface shall provide high-contrast visual cues visible from not less than 1.5 meters distance. | Inspection | **VERIFIED** |
| **`ASTRA-OPS-002`** | Vocal assistance speech strings shall maintain an articulation rate between 140 and 170 words per minute for optimal cockpit intelligibility. | Test | **VERIFIED** |
| **`ASTRA-OPS-003`** | The system shall provide a single-command pre-flight self-test (`astra final-check` / `astra competition-check`) executing in $<3$ seconds. | Test | **VERIFIED** |
