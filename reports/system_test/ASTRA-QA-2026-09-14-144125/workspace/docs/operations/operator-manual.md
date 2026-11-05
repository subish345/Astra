# ASTRA-EA — Operational Roles & Operator Manual

## Phase 19: Mission Operations & Ground Segment Integration (D19.03, D19.04, D19.07)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Operational Roles & Responsibilities (Section 5, 6)

ASTRA-EA structures operations across 6 formal roles (consolidated into `LOCAL_OPERATOR` for standalone competitions):

### 1. Astronaut / Experiment Operator (`ASTRONAUT_OPERATOR`)
- **Primary Interface:** Workstation Mission Console HUD & Offline Audio Guidance.
- **Responsibilities:**
  - Physically stages biological/chemical apparatus.
  - Follows step-by-step cognitive visual prompts.
  - Listens and immediately reacts to audio recovery directives.
  - Acknowledges deviation notices on the touch HUD.

### 2. Mission Operator (`MISSION_OPERATOR`)
- **Primary Interface:** Onboard Flight Console / Ground Command Station.
- **Responsibilities:**
  - Authorizes experiment initialization and start.
  - Monitors mission timeline progress.
  - Coordinates with flight director during unresolved anomalies.
  - Authorizes pausing or resuming experiments.

### 3. Ground Monitor (`GROUND_MONITOR`)
- **Primary Interface:** Remote Ground Observability Console (`apps/ground_monitor`).
- **Responsibilities:**
  - Observes live optical video and time-indexed assurance decisions.
  - Acknowledges incoming telemetry alerts.
  - Tracks sequence reconciliation and channel health.
  - Requests status and evidence snapshots for ground investigator review.
  - **Restriction:** Strictly read-only; cannot modify onboard execution state.

### 4. System Engineer (`SYSTEM_ENGINEER`)
- **Primary Interface:** Command Line (`astra`), Platform Health Dashboard.
- **Responsibilities:**
  - Executes pre-mission checks (`astra mission precheck`).
  - Monitors CPU silicon temperatures, memory RSS, and storage partition headroom.
  - Enters/exits maintenance mode (`astra maintenance enter/exit`) for diagnostics.
  - Investigates diagnostic logs (`flight_data/diagnostics/flight.log`).

### 5. Data Reviewer (`DATA_REVIEWER`)
- **Primary Interface:** Mission Review GUI / CLI (`astra mission review`, `astra mission report`).
- **Responsibilities:**
  - Audits post-mission JSON and HTML reports.
  - Inspects cryptographic evidence clips tied to procedural deviations.
  - Archives exported run bundles (`RUN_XXXX/`).

### 6. Maintainer (`MAINTAINER`)
- **Primary Interface:** Maintenance Mode CLI.
- **Responsibilities:**
  - Updates validated model weights or procedure YAML packages during scheduled ground maintenance.
  - Executes optical camera loopback diagnostics and storage scrubbing.

---

## 2. Authority Model & Permission Matrix (Section 7)

| Permission | Astronaut | Mission Operator | Ground Monitor | System Engineer | Data Reviewer | Maintainer | Local Operator |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `START_EXPERIMENT` | **YES** | **YES** | NO | NO | NO | NO | **YES** |
| `PAUSE_EXPERIMENT` | **YES** | **YES** | NO | NO | NO | NO | **YES** |
| `RESUME_EXPERIMENT` | **YES** | **YES** | NO | NO | NO | NO | **YES** |
| `STOP_EXPERIMENT` | **YES** | **YES** | NO | NO | NO | NO | **YES** |
| `ACKNOWLEDGE_ALERT` | **YES** | **YES** | **YES** | **YES** | NO | NO | **YES** |
| `REQUEST_EVIDENCE` | NO | **YES** | **YES** | **YES** | **YES** | NO | **YES** |
| `REQUEST_REPORT` | NO | **YES** | **YES** | **YES** | **YES** | NO | **YES** |
| `VIEW_LOGS` | NO | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** |
| `EXPORT_REPORT` | NO | **YES** | NO | **YES** | **YES** | NO | **YES** |
| `ENTER_MAINTENANCE`| NO | NO | NO | **YES** | NO | **YES** | **YES** |

---

## 3. Operator Workflows

### Pre-Mission Step-by-Step
1. Power up computer and camera.
2. Run automated validation:
   ```bash
   astra mission precheck
   ```
3. Confirm all 9 subsystems report `[PASS]` and overall verdict is `[READY]`.
4. Launch console interface:
   ```bash
   astra mission --procedure configs/experiments/demo.yaml
   ```

### Anomaly & Deviation Response
1. If the system announces an audio warning (e.g. *"Warning: Incorrect apparatus"*), check the HUD.
2. Observe the red deviation banner displaying:
   - **Observed Object:** (e.g. Pipette Tip Box)
   - **Expected Object:** (e.g. Centrifuge Tube)
   - **Recovery Directive:** (e.g. Return pipette box; grasp centrifuge tube)
3. Acknowledge the alert by pressing **ACKNOWLEDGE** on screen.
4. Perform the physical recovery directive.
5. Watch the HUD update to green `[VERIFIED]` once the assurance engine confirms correct apparatus placement.
