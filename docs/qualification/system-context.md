# ASTRA-EA: Spacecraft Integration Architecture & System Context

**Document Classification:** Aerospace Payload Architecture & Interface Specification  
**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Executive Summary & Integration Principle

ASTRA-EA is architected as an autonomous edge payload subsystem for scientific laboratory experiment monitoring aboard the **Bharatiya Antariksh Station (BAS)** or modular exploration spacecraft.

To ensure qualification readiness without binding the software to proprietary spacecraft hardware before official vehicle specifications are finalized, the architecture enforces a strict architectural boundary:

```
[ ASTRA-EA INTERNAL APPLICATION CORE ]  <==== EXPLICIT LOGICAL BOUNDARY ====>  [ HOST SPACECRAFT BUS SERVICES ]
  - Neural Optical Perception (Detector + Pose)                                 - Primary Unregulated / Regulated Power Bus
  - Spatial Interaction & Contact Estimator                                      - Structural Conduction / Thermal Management
  - Temporal Activity Accumulator                                                - Spacecraft Master Clock / SCET Time Source
  - Deterministic Procedure State Machine                                        - Onboard Telemetry & Command Data Bus
  - Epistemic Assurance Engine (Tri-State)                                       - SpaceWire / GMSL Optical Camera Sensor Links
  - Local Cockpit Voice & Visual Guidance                                        - Spacecraft Long-Range S/X/Ka-Band Ground Link
  - Tamper-Evident Local SQLite Audit Store
```

---

## 2. System Context Diagram

```mermaid
graph TD
    subgraph SpacecraftBus ["Host Spacecraft Infrastructure (BAS Payload Rack)"]
        PowerSource["Spacecraft Power Bus (28V / 120V DC)"]
        TimeSource["Spacecraft Master Clock (SCET / GPS / PPS)"]
        ThermalBus["Spacecraft Cold Plate (Conduction Cooling)"]
        VehicleBus["Vehicle Data Bus (MIL-STD-1553B / SpaceWire / CAN)"]
        GroundTransceiver["Space-to-Ground Telemetry (S/X-Band)"]
        OpticalHead["Space-Qualified Camera Optical Head"]
    end

    subgraph PayloadEnclosure ["ASTRA-EA Edge Payload Subsystem"]
        PSU["Power Conditioning & Telemetry Monitor"]
        ClockSync["Dual-Clock Time Synchronization Module"]
        ThermalSensors["Internal Temperature Probes"]
        BusAdapter["Vehicle Bus Interface Adapter (Logical)"]

        subgraph EdgeComputeEngine ["Edge Compute Engine (Isolated Worker Architecture)"]
            Ingestion["Video Ingestion & Frame Normalizer"]
            Perception["Perception Engine (Detector + Pose)"]
            Interaction["Interaction & Geometric Engine"]
            Activity["Activity Accumulator"]
            Procedure["Procedure State Machine"]
            Assurance["Tri-State Assurance Engine"]
            Assistance["Cockpit Guidance & Voice Driver"]
            LocalStorage["Local NVMe SSD Audit Database (WAL)"]
        end
    end

    subgraph GroundSystem ["Earth Ground Station / Mission Control"]
        GroundMonitorUI["Ground Monitor Dashboard & Telemetry Viewer"]
    end

    PowerSource -->|Filtered DC| PSU
    PSU --> EdgeComputeEngine
    TimeSource -->|SCET / Monotonic| ClockSync
    ClockSync --> EdgeComputeEngine
    OpticalHead -->|GMSL / USB3| Ingestion
    ThermalBus ---|Conductive Path| PayloadEnclosure

    Assurance -->|Telemetry Packets| BusAdapter
    Assurance -->|Local Alerts| Assistance
    Assurance -->|Microsecond Audit Logs| LocalStorage
    BusAdapter --> VehicleBus
    VehicleBus --> GroundTransceiver
    GroundTransceiver -.->|Orbital Pass Downlink| GroundMonitorUI
```

---

## 3. Subsystem Boundary Partitioning

| Subsystem Domain | Execution Environment | Criticality Tier | Failure Impact on Spacecraft |
| :--- | :--- | :---: | :--- |
| **Assurance Core** | Edge Worker (Isolated Memory) | **CRITICAL** | None (Confined to payload experiment verification) |
| **Perception Engine** | GPU / NPU Accelerator Worker | **CRITICAL** | None (Fails over to baseline heuristic without crash) |
| **Local Storage** | Local NVMe SSD Partition | **IMPORTANT** | None (Write-Ahead Logging prevents filesystem corruption) |
| **Cockpit Audio Guidance** | Local Audio DAC / Speaker | **OPTIONAL** | None (Muted audio auto-switches to visual HUD banners) |
| **Ground Streaming** | WebSocket / MJPEG Server | **AUXILIARY** | Zero (Severed ground link leaves onboard assurance active) |

---

## 4. Operational Invariant: Air-Gap Autonomy

The fundamental spacecraft integration rule for ASTRA-EA:
> **The onboard procedural assurance engine, neural detector, temporal activity parser, and local audit storage SHALL NOT require external network connectivity, ground communication passes, or cloud infrastructure to execute, verify, or recover an experiment.**
