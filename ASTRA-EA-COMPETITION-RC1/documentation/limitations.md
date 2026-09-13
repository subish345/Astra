# ASTRA-EA: System Limitations & Engineering Disclosures

**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Document Classification:** Final Technical Engineering Transparency Disclosure  
**Release:** 1.0.0-RC1 (SIH26174 Ground Demonstrator)

---

## 1. Executive Disclosure & Claim Policy

ASTRA-EA is developed as an **engineering-grade ground demonstrator** validating the software architecture, edge-AI perception pipeline, procedural assurance engine, and explainable audit logging for astronaut experiment monitoring.

### Authorized Technical Claims
- **Ground Demonstrator:** Validated laboratory ground prototype (TRL 4).
- **Edge-Native Inference:** Functional offline AI execution on commercial-off-the-shelf (COTS) edge and workstation compute hardware.
- **Controlled Validation:** Demonstrated procedural deviation detection, recovery verification, and state tracking under defined, controlled experiment scenarios.
- **Hybrid Dataset:** Trained and benchmarked on an experiment-specific dataset combining physical laboratory recordings with synthetic parametric variations.

### Prohibited / Disclaimed Claims
- **NOT Flight-Ready:** Software and hardware have not undergone aerospace flight qualification.
- **NOT ISRO/NASA Certified:** Not certified or approved by any national space agency or regulatory body.
- **NOT Spacecraft Qualified:** Has not been tested for radiation tolerance, thermal-vacuum endurance, launch vibration, or electromagnetic compatibility.
- **NOT Zero-Gravity Proven:** Fluid dynamics, floating object physics, and altered biomechanics in microgravity have not been physically validated in orbital or parabolic flight.
- **NOT 100% Accurate:** Optical perception is inherently probabilistic and subject to edge-case failures under extreme environmental degradation.

---

## 2. Hardware & Environmental Limitations

### 2.1 Development & Demonstration Hardware
- **Target Systems:** Benchmarked on standard Linux workstations (x86_64, NVIDIA RTX GPU) and simulated edge profiles.
- **Spacecraft Compute Differences:** Spacecraft payload processors (e.g., BAE RAD750, Vorago VA416x0, or space-qualified Unibap iX5 / Cobham Gaisler architectures) have severe clock speed limitations (typically 100–800 MHz) and strict power envelopes (5–25 W). Production deployment would require model pruning, quantization (INT8/INT4), and porting to radiation-hardened DSPs or space-grade FPGAs.

### 2.2 Radiation & Thermal Environment
- **Single Event Effects (SEE):** COTS GPU/CPU memory lacks ECC hardening against heavy-ion single-event upsets (SEU) or latch-ups (SEL) present in Low Earth Orbit (LEO) and deep space.
- **Thermal Dissipation:** Vacuum operation requires conductive cooling paths; convective fan cooling used in test workstations is non-functional in space environments.

---

## 3. Optical & Sensor Limitations

### 3.1 Sensor Modality (Webcam & COTS Optical)
- **Dynamic Range:** Standard webcams (RGB 8-bit) suffer from sensor saturation under direct high-contrast solar glare or severe underexposure in unlit experiment cubicles.
- **Fixed Focal Length:** Lack of optical autofocus or telephoto capabilities limits fine-grained inspection of millimeter-scale fluid meniscus levels or microscopic pipette graduations.
- **Rolling Shutter:** Fast hand or tool movements induce rolling shutter distortion, degrading bounding box localization accuracy.

### 3.2 Viewpoint & Extreme Occlusion
- **Line-of-Sight Dependency:** Optical assurance requires an unblocked optical path between the camera and the astronaut's hands/tools. If the operator's torso, arm, or an overhead rack completely occludes the tool interaction for longer than the temporal dwell threshold, the system transitions to `UNCERTAIN` and cannot verify the action.
- **Multi-Angle Coverage:** While lateral viewpoints (`VIEW_LEFT`, `VIEW_RIGHT`) were validated, full spatial invariance requires multi-camera sensor fusion, which is planned for future iterations.

---

## 4. Dataset & Perception Model Limitations

### 4.1 Synthetic Data Domain Gap
- **Rendering Artifacts:** Synthetic variations generated in the dataset pipeline utilize procedural rendering and color jitter. While highly effective for expanding sample diversity and edge-case illumination, synthetic textures do not fully capture non-rigid glove deformations or complex specular reflections off glossy metallic spacecraft apparatus.

### 4.2 Fine-Grained Object Differentiation
- **Geometric Similarity:** Tools sharing identical cylindrical form factors and transparent materials (e.g., standard micropipette tips vs. capillary tubes) require high-resolution input and optimal lighting to reliably distinguish without barcoding or RFID tagging.
- **Open-World Generalization:** The model recognizes the classes present in `ASTRA-DATASET-v1.0`. Novel lab equipment introduced without retraining will either be categorized as `unknown_object` or trigger low-confidence misclassifications.

---

## 5. Microgravity Physics Disclosures

### 5.1 Biomechanical & Motion Alterations
- **Neutral Body Posture (NBP):** Astronaut arm angles and posture in microgravity differ significantly from 1G terrestrial ergonomics. Ground-trained pose estimators may experience minor keypoint drift when observing free-floating astronauts.
- **Tethering & Floating Dynamics:** In orbital laboratories, tools must be velcroed, magnetically secured, or tethered when released. The current spatial interaction engine assumes standard terrestrial table-top workspace ergonomics.

### 5.2 Fluid Dynamics
- **Surface Tension Dominance:** In microgravity, liquids form capillary spheres rather than settling into standard terrestrial planar meniscus levels. Meniscus-level reading and liquid volume dispensing assurance require specialized microfluidic computer vision models.

---

## 6. Future Aerospace Qualification Roadmap

| Milestone | TRL Level | Engineering Scope | Key Requirements |
| :--- | :---: | :--- | :--- |
| **ASTRA-EA (Current)** | **TRL 4** | Laboratory ground demonstration | Edge-AI assurance, state machine, deviation detection |
| **High-Fidelity Mockup** | **TRL 5** | Neutral Buoyancy / Parabolic Flight | Microgravity posture, floating tool tracking, multi-camera fusion |
| **Payload Prototype** | **TRL 6** | Space-grade compute testbed | Quantization to space FPGA/DSP, TVAC chamber testing, radiation screening |
| **Flight Demonstration** | **TRL 7** | Orbital technology demonstrator | Operational validation on Bharatiya Antariksh Station (BAS) or ISS payload rack |
| **Mission Critical** | **TRL 8/9** | Flight certified operational system | Formal aerospace software qualification (DO-178C Level B / ECSS-E-ST-40C) |
