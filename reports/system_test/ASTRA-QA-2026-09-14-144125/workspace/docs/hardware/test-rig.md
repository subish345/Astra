# ASTRA-EA: Physical Experiment Station & Test Rig Specification

**System:** Autonomous Spacecraft Experiment Assurance & Assistance  
**Classification:** Hardware Engineering & Physical Validation Document  
**Target Environment:** Ground Experiment Station (TRL 4 / HIL Testbed)

---

## 1. Test Rig Overview & Purpose
The ASTRA-EA Physical Test Rig provides a standardized, geometrically repeatable ground station for validating the complete end-to-end edge assurance pipeline against physical human movement, real optical lens physics, ambient illumination shifts, and physical tool handling.

```
                  [Rigid Overhead Mount]
                            |
                     [Optical Camera]
                     (Height: 50 cm)
                     (Pitch: 40° down)
                            |
                            v
+-------------------------------------------------------------+
|                     WORKSPACE SURFACE                       |
|                                                             |
|   [-20, 10]              [0, 15]                [20, 10]    |
|  [Tube Rack]          [Main Work Area]       [Pipette Stand]|
|                                                             |
|   [-10, 0]                                      [10, 0]     |
|  [RED BOX]                                   [YELLOW BOX]   |
| (Specimen Tube)                           (Centrifuge Tube) |
|                                                             |
|                        [0, -15]                             |
|                  [Operator Grasp Zone]                      |
+-------------------------------------------------------------+
```

---

## 2. Reference Coordinate Frame
A Cartesian coordinate system is defined with the origin $(0, 0, 0)$ positioned at the geometric center of the active tabletop workspace:
- **X-Axis (Lateral):** Positive pointing right (towards operator's right hand), negative pointing left. Range: $[-30\text{ cm}, +30\text{ cm}]$.
- **Y-Axis (Depth):** Positive pointing away from the operator (towards the background), negative pointing towards the operator. Range: $[-20\text{ cm}, +20\text{ cm}]$.
- **Z-Axis (Elevation):** Positive pointing upward perpendicular to the work surface. Range: $[0\text{ cm}, +60\text{ cm}]$.

---

## 3. Physical Apparatus & Object Locations

| Apparatus | Semantic Identifier | Dimensions ($W \times D \times H$) | Reference Coordinates $(X, Y, Z)$ | Role in Demonstration |
| :--- | :--- | :---: | :---: | :--- |
| **Work Surface** | `tabletop_mat` | $80 \times 60 \times 0.5\text{ cm}$ | Centered at $(0, 0, 0)$ | Non-reflective neutral gray mat |
| **Main Target** | `RED_BOX` (`specimen_tube`) | $3 \times 3 \times 12\text{ cm}$ | $(-10\text{ cm}, 0\text{ cm}, 0\text{ cm})$ | Nominal Step 1 target (Green cap) |
| **Deviation Object** | `YELLOW_BOX` (`centrifuge_tube`)| $3 \times 3 \times 12\text{ cm}$ | $(+10\text{ cm}, 0\text{ cm}, 0\text{ cm})$ | Intentional Step 2 error (Blue cap) |
| **Dispensing Tool** | `pipette` | $4 \times 3 \times 24\text{ cm}$ | $(+20\text{ cm}, +10\text{ cm}, 0\text{ cm})$ | Nominal Step 2 / Recovery target |
| **Apparatus Rack** | `tube_rack` | $20 \times 10 \times 8\text{ cm}$ | $(-20\text{ cm}, +10\text{ cm}, 0\text{ cm})$ | Holding apparatus for sample vials |
| **Incubator Slot** | `MAIN_BOX` | $25 \times 20 \times 15\text{ cm}$ | $(0\text{ cm}, +15\text{ cm}, 0\text{ cm})$ | Step 4 destination apparatus |

---

## 4. Optical Sensor & Camera Mounting

### 4.1 Mechanical Mounting Requirements
- **Mount Type:** Rigid extruded aluminum arm or heavy-duty C-clamp desktop boom with 3-axis locking ball head.
- **Vibration Isolation:** Dampened mounting plate to eliminate operator table-bump vibrations.
- **Prohibited:** Flexible friction arms, hand-held positioning, or lightweight plastic tripods.

### 4.2 Geometric Mounting Specifications
- **Optical Center Position:** $(0\text{ cm}, -25\text{ cm}, +50\text{ cm})$
- **Downward Pitch Angle:** $40^\circ \pm 2^\circ$ below horizontal.
- **Roll / Yaw Angle:** $0^\circ \pm 1^\circ$ (aligned with the X-axis).
- **Working Optical Distance:** $55\text{ cm} \pm 3\text{ cm}$ to workspace center.
- **Optical FoV:** Horizontal FoV $\ge 78^\circ$, covering the full $60 \times 40\text{ cm}$ manipulation zone.

---

## 5. Illumination & Ambient Lighting Standards

The test rig incorporates calibrated lighting levels measured via digital luxmeter at tabletop origin:

| Lighting Profile | Target Lux | Source Configuration | Validation Purpose |
| :--- | :---: | :--- | :--- |
| **NORMAL (Baseline)** | $300 - 450\text{ Lux}$ | Overhead 4000K diffused LED | Standard laboratory benchmark |
| **BRIGHT** | $750 - 1000\text{ Lux}$| Direct dual-panel flood lighting | High-contrast solar glare simulation |
| **DIM** | $30 - 60\text{ Lux}$ | Ambient room spill only | Low-power spacecraft cubicle testing |
| **SIDE LIGHT** | $250\text{ Lux (Lateral)}$ | Single $45^\circ$ directional beam | Harsh shadowing / hand occlusion test |
| **SHADOW** | $<20\text{ Lux (Spot)}$ | Cast shadow from operator torso | Uncertainty state boundary evaluation |

---

## 6. Compute, Network & Power Infrastructure

### 6.1 Compute Infrastructure
- **Development Workstation:** Linux x86_64, 8 cores, 32GB RAM, NVIDIA RTX GPU.
- **Edge Compute Prototype:** ARM64 / x86 embedded industrial compute node (USB 3.0 / PCIe V4L2 ingestion).
- **Storage:** NVMe SSD dedicated partition for high-rate MP4 video and SQLite WAL transactions.

### 6.2 Network Infrastructure
- **Air-Gap Mode:** Completely disconnected physical network for local mission autonomy.
- **Ground Link Mode:** 1 Gbps Cat6 Ethernet connection to isolated local switch hosting Ground Monitor display.

### 6.3 Power Infrastructure
- Grounded surge-protected 230V AC distribution with dedicated 65W+ USB-C PD / DC power bricks.
