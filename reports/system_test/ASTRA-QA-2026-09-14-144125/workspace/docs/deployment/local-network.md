# ASTRA-EA — Dual-Machine LAN Deployment Guide

## Multi-Node Ground Monitoring and Local/IP Streaming Setup

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. System Deployment Topology

ASTRA-EA supports a distributed operational configuration where the autonomous spacecraft runtime (**Onboard**) and the remote observation station (**Ground Monitor**) run on separate physical machines interconnected via a local area network (LAN), Ethernet tether, or lab Wi-Fi network.

```text
┌────────────────────────────────────────────────────────┐
│ MACHINE 1: ONBOARD SPACECRAFT RUNTIME                  │
│ IP: 192.168.1.100 (Example LAN IP)                    │
│                                                        │
│ • Camera Sensor / Synthetic Pipeline                   │
│ • Real-time AI Perception & Activity Tracking          │
│ • Procedure Semantics & Assurance Engine               │
│ • Local Session Logger & Video Recorder                │
│ • Non-blocking Stream Servers:                         │
│     - Video Stream Server (TCP :8554)                  │
│     - Event SSE Server   (TCP :8765)                  │
└────────────────────────────────────────────────────────┘
                           │
       [ Local Gigabit Ethernet / Isolated LAN ]
                           │
┌────────────────────────────────────────────────────────┐
│ MACHINE 2: GROUND OBSERVATION CONSOLE                  │
│ IP: 192.168.1.200 (Example LAN IP)                    │
│                                                        │
│ • Ground Monitor GUI (apps/ground_monitor/)           │
│ • Live Video Player & Latency Telemetry                │
│ • Mission Timeline & Event Stream Consumer             │
│ • Evidence Bundle Viewer                               │
│ • Connection Health Watchdog (Auto-reconnect)          │
│ • READ-ONLY (Zero Execution Commands to Onboard)       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Network Prerequisites & Port Configuration

### 2.1 Port Requirements
Ensure the following TCP ports are open on the Onboard host machine's firewall:

| Port | Protocol | Purpose | Direction |
| :--- | :--- | :--- | :--- |
| **8554** | TCP / HTTP | Multipart MJPEG Video Stream | Inbound to Onboard |
| **8765** | TCP / HTTP | Server-Sent Events (SSE) & Replay API | Inbound to Onboard |

```bash
# On Linux hosts running UFW:
sudo ufw allow 8554/tcp comment "ASTRA Video Stream"
sudo ufw allow 8765/tcp comment "ASTRA Event Telemetry"
```

### 2.2 Onboard Configuration (`configs/system.yaml`)
To allow remote ground clients across the local subnet to connect, configure the server host binding on Machine 1:

```yaml
stream:
  enabled: true
  protocol: "mjpeg"
  host: "0.0.0.0"       # Bind to all network interfaces for LAN access
  port: 8554
  width: 1280
  height: 720
  fps: 15
  quality_mode: "MEDIUM"

events:
  enabled: true
  port: 8765
  host: "0.0.0.0"

heartbeat:
  interval_seconds: 2.0
  timeout_seconds: 6.0
```

> **Security Note:** Binding to `0.0.0.0` is intended strictly for isolated private subnets or direct Ethernet tethers. Never expose ports 8554 and 8765 directly to the public internet.

---

## 3. Step-by-Step Deployment Instructions

### 3.1 Step 1: Pre-Flight Verification on Machine 1 (Onboard)
On the onboard computer, run the diagnostic doctor:
```bash
python3 main.py doctor
python3 main.py stream doctor
```
Confirm that perception models, cameras, and network servers indicate ready status.

### 3.2 Step 2: Start Onboard Mission Pipeline (Machine 1)
Launch either the live astronaut mission console or a streaming simulation scenario:

```bash
# Option A: Live astronaut mission with streaming enabled
python3 main.py mission

# Option B: Headless streaming simulation scenario
python3 main.py sim run --scenario NOMINAL_001 --stream
```
The console will indicate that the video server has bound to `:8554` and event telemetry to `:8765`.

### 3.3 Step 3: Launch Ground Monitor (Machine 2)
On the ground laptop or monitoring workstation, launch the Ground Monitor client specifying Machine 1's IP address:

```bash
python3 main.py ground-monitor --host 192.168.1.100 --video-port 8554 --events-port 8765
```

The Ground Monitor window will initialize, connect both video and event channels, and display:
- **Link Status:** `LINK: 🟢 ONLINE`
- **Video Feed:** Live MJPEG stream with overlay stats
- **Mission Progress:** Current experiment, step, and activity
- **Timeline:** Telemetry events updated in real time

---

## 4. Operational Demonstration & Link Loss Protocol

To demonstrate robust spacecraft-ground autonomy during an evaluation or demonstration:

1. **Verify Nominal Telemetry:** Observe live video and step verification updates flowing smoothly to Machine 2.
2. **Simulate Uplink/Downlink Loss:** Unplug the Ethernet cable or disable the network interface on Machine 2.
   - **Ground Monitor Result:** Instantly detects missing heartbeat, transitions header status to `LINK LOST: RECONNECTING...`, and retains the last known mission state on screen without crashing.
   - **Onboard Runtime Result:** The experiment continues with zero interruption. AI perception, procedure assurance, deviation detection, local event logging, and local video recording proceed completely normally.
3. **Restore Network Connectivity:** Reconnect the Ethernet cable or re-enable the network interface.
   - **Ground Monitor Result:** Automatically reconnects, queries `GET /events/replay?since={seq}` to catch up on any missed events, updates the timeline, and displays `LINK RESTORED`.
