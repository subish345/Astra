# ASTRA-EA: Domain Gap Analysis

**Classification:** Computer Vision & Hardware Engineering Analysis  
**Scope:** Synthetic Procedural Variations vs. COTS Webcam vs. Physical Test Rig

---

## 1. Domain Overview
In developing an offline edge-AI assurance platform for spaceflight experiments, training models solely on terrestrial laboratory webcams or solely on synthetic computer graphics creates critical blind spots.

ASTRA-EA operates across three distinct visual domains:
1. **Synthetic Simulation Domain:** Parametrically rendered frames with procedural lighting, color jitter, and injected anomalies.
2. **COTS Webcam Laboratory Domain:** Standard terrestrial webcam video captured at an operator desk.
3. **Physical Experiment Rig Domain:** Standardized reference coordinate station with calibrated Lux levels, rigid mounting, and realistic laboratory glassware.

```
       [SYNTHETIC DOMAIN]                [WEBCAM DOMAIN]
     - Procedural Lighting             - Unconstrained Angles
     - Injected Box Swaps              - Table Vibration Noise
     - Idealized Glassware             - Ambient Room Reflections
              \                               /
               \                             /
                v                           v
              +-------------------------------+
              |   PHYSICAL TEST RIG DOMAIN    |
              | - Calibrated Lux (30-850 Lux) |
              | - Rigid Overhead Clamp (50cm) |
              | - Reference Coordinate Frame  |
              | - Real Human Motion Styles    |
              +-------------------------------+
```

---

## 2. Quantitative Domain Divergence Comparison

| Visual Characteristic | Synthetic Generator | COTS Webcam | Physical Test Rig | Domain Gap Impact & Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Glass Specular Reflections** | Simplified Phong specular highlights | Unpredictable fluorescent tube glare | Diffused 4000K LED with anti-glare gray mat | **Mitigated:** Diffused illumination prevents glare blowout on tube meniscus. |
| **Glove & Hand Deformation** | Procedural mesh / keypoints | Real bare hands | Nitrile-gloved astronaut hands | **Observed:** Glove wrinkles reduce keypoint conf by 4.2%; compensated by 10-frame temporal dwell. |
| **Illumination Dynamics** | Mathematical falloff | Non-linear webcam auto-exposure hunting | Locked manual exposure & calibrated Lux | **Critical:** Auto-exposure oscillation caused false flicker; locked exposure resolved it. |
| **Motion Blur & Shutter** | Zero blur (instantaneous render) | Rolling shutter skew on fast moves | 30 FPS global/fast-shutter sensor | **Mitigated:** Fast operator motion induces slight bounding box expansion; compensated by contact IoU. |
| **Background Clutter** | Uniform simulated backdrop | Room furniture, cables, coffee cups | Clean, neutral gray workspace boundaries | **Resolved:** Calibrated work surface eliminates background false-positive object tracks. |

---

## 3. Epistemic Findings & Conclusions
- **Synthetic Pre-Training Value:** Synthetic variations successfully hardened the neural detector against lighting drops (down to 15 Lux) and rare wrong-object permutations.
- **Physical Test Rig Value:** Physical testing exposed hardware real-world constraints—such as camera driver V4L2 re-enumeration latency (850 ms) during cable disconnection and rolling shutter distortions during rapid operator reach—which pure synthetic simulations could never reveal.
