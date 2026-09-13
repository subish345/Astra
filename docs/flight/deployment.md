# ASTRA-EA — Flight Integration Deployment & Installation Guide

### Document ID: `ASTRA-DEP-001`
**Milestone**: Phase 18 — Flight Integration Preparation + Onboard Software Packaging  
**Package Target**: `ASTRA-EA-FLIGHT-INTEGRATION-001`  

---

## 1. Clean Environment Installation Procedure (Section 56)

To deploy ASTRA-EA onto a clean target compute environment:

```
INSTALL ──► VALIDATE ──► DOCTOR ──► START ──► HIL TEST
```

### Step 1: Package Extraction
```bash
# Extract the release tarball or copy package directory
cp -r deployment/flight/ASTRA-EA-FLIGHT-INTEGRATION-001 /opt/astra-ea
cd /opt/astra-ea
```

### Step 2: Package Validation
Run the automated package integrity validator:
```bash
astra flight-package validate --package-dir /opt/astra-ea
```
Expected output:
```
======================================================================
 ASTRA-EA FLIGHT PACKAGE INTEGRITY VALIDATOR
======================================================================
Target Package:    /opt/astra-ea
Artifacts Checked: 196
Errors Found:      0
----------------------------------------------------------------------
Validation Result: [PASS]
======================================================================
```

### Step 3: Platform Diagnostics (Doctor)
Inspect target compute capabilities and verify dependencies:
```bash
astra doctor
astra edge doctor
```

### Step 4: Systemd Service Deployment (Optional)
To configure ASTRA-EA as a managed flight daemon on Linux:
```ini
# /etc/systemd/system/astra-ea.service
[Unit]
Description=ASTRA-EA Autonomous Spacecraft Experiment Assurance Daemon
After=network.target

[Service]
Type=simple
User=astra
WorkingDirectory=/opt/astra-ea
Environment="ASTRA_RUNTIME_MODE=FLIGHT_INTEGRATION"
Environment="ASTRA_PLATFORM_PROFILE=FLIGHT_TARGET_TBD"
ExecStart=/usr/bin/bash /opt/astra-ea/scripts/start_flight.sh
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable astra-ea
sudo systemctl start astra-ea
```

### Step 5: Hardware-in-the-Loop Integration Verification
Execute the automated 12-scenario integration verification suite:
```bash
astra hil flight-integration-test --all
```
Expected output:
```
Total Scenarios: 12 | Passed: 12 | Failed: 0
Overall Verdict: [PASS]
```

---

## 2. Environment Variables

| Variable | Permitted Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `ASTRA_RUNTIME_MODE` | `FLIGHT_INTEGRATION`, `VALIDATION`, `DEMO`, `DEVELOPMENT` | `FLIGHT_INTEGRATION` | Enforces runtime security boundaries and disables developer debug tools |
| `ASTRA_PLATFORM_PROFILE` | `FLIGHT_TARGET_TBD`, `EDGE_PROTOTYPE`, `DEVELOPMENT_LAPTOP` | `FLIGHT_TARGET_TBD` | Sets target hardware profile contracts and constraints |
| `ASTRA_LOG_LEVEL` | `INFO`, `WARNING`, `ERROR` | `INFO` | Console logging verbosity level |

---

## 3. Post-Deployment Verification Checklist

- [ ] `flight_manifest.json` and `flight_configuration_manifest.json` present.
- [ ] Checksums in `checksums/sha256sums.txt` 100% verified.
- [ ] No Dataset Studio or training pipelines packaged.
- [ ] Camera driver connects to video source or simulated HIL harness.
- [ ] Telemetry packets emitting at nominal rates to `flight_data/telemetry/`.
- [ ] Active mission state correctly persists to `flight_data/mission/`.
