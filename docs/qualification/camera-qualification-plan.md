# ASTRA-EA: Optical Sensing & Camera Qualification Test Plan

**Document ID:** `ASTRA-QTP-CAM-001`  
**Test Identifier:** `QUAL-CAM-001`  
**Standard:** ISO 12233 (Photography — Electronic still picture cameras — Resolution and spatial frequency responses) / ECSS-E-ST-10-03C  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Sensor Specification:** $1920 \times 1080$ CMOS Sensor, $78^\circ$ Diagonal FOV, Fixed Focal Length Lens  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

The camera is the primary sensory transducer of ASTRA-EA. The system cannot perform valid procedural assurance if optical input suffers from thermal defocus, lens decentering, motion blur, exposure oscillation, or severe specular reflections.

Specific goals:
1. Verify Modulation Transfer Function ($\text{MTF50}$) optical resolution across operating temperatures ($-10^\circ\text{C}$ to $+50^\circ\text{C}$).
2. Verify exposure and gain stability across dynamic illumination extremes ($45\text{ Lux}$ to $850\text{ Lux}$).
3. Characterize lens distortion and calibrate viewpoint profiles (`view_left`, `view_center`, `view_right`) with sub-millimeter reprojection error.
4. Verify mechanical rigidity of the camera bracket and assess cable strain relief under vibration.

---

## 2. Optical Test Setup & Instrumentation

### 2.1 Laboratory Collimator Bench
- **Optical Test Bench:** Vibration-isolated optical breadboard with high-flatness surface plate.
- **Test Charts:** ISO 12233 Edge/Slanted-Edge Resolution Chart, 24-patch Macbeth ColorChecker, Macbeth Grayscale Step Wedge.
- **Photometric Lighting:** Diffuse LED light panels with high Color Rendering Index ($\text{CRI} \ge 95$) adjustable continuously between $20\text{ Lux}$ and $1200\text{ Lux}$.
- **Light Meter:** Calibrated digital illuminance meter (Lux) placed coplanar with the experiment target.

---

## 3. Optical Verification Domains

### 3.1 Spatial Resolution & MTF50
- **Measurement:** Slanted-edge spatial frequency response calculated at center ($0.0\text{F}$), half-field ($0.5\text{F}$), and edge ($0.85\text{F}$).
- **Acceptance Criterion:** $\text{MTF50} \ge 0.35\text{ cycles/pixel}$ across all fields; thermal defocus shift $\Delta \text{MTF50} < 8\%$.

### 3.2 Dynamic Exposure & Anti-Flicker Stability
- **Measurement:** Step changes in ambient illumination: $850\text{ Lux} \longrightarrow 45\text{ Lux} \longrightarrow 850\text{ Lux}$.
- **Acceptance Criterion:** Auto-exposure settles to target luminance within $\le 5$ frames ($166\text{ ms}$) without brightness hunting or overshoot oscillations.

### 3.3 Specular Reflections & Texture Invariance
- Test acrylic specimen tubes, glass petri dishes, and metallic centrifuge tubes under direct spotlight glare.
- Verify that localized specular glares do not reduce neural detection confidence below $0.50$.

### 3.4 Camera Mechanical Mount Rigidity & Cable Strain
- **Mount:** CNC-machined 6061-T6 aluminum bracket with locating dowel pins to guarantee angular repeatability.
- **Fasteners:** Grade 316 stainless steel screws with Belleville spring washers and Loctite 242 threadlocker.
- **Cable Strain Relief:** Dual cushioned P-clamps securing GMSL2/USB3 cable within $50\text{ mm}$ of the camera body, limiting bend radius to $\ge 40\text{ mm}$.

---

## 4. Acceptance Criteria

1. **Optical Sharpness:** Center MTF50 $\ge 0.35\text{ cyc/px}$; peripheral MTF50 $\ge 0.25\text{ cyc/px}$.
2. **Illumination Invariance:** Bounding box detection recall $\ge 90\%$ from $45\text{ Lux}$ to $850\text{ Lux}$.
3. **Timestamp Jitter:** Inter-frame timestamp variation $<2.0\text{ ms}$ at 30.0 FPS.
4. **Mechanical Alignment:** Post-vibration angular deviation $<0.25^\circ$.
