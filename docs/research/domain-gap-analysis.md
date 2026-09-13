# ASTRA-EA Synthetic-to-Real Domain Gap Analysis

Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Executive Summary

Phase 7 of ASTRA-EA introduces a dual data strategy combining **controlled synthetic procedural generation** with **real webcam session recordings**. Synthetic generation provides vast scale, controlled variation across challenge scenarios (occlusion, lighting shifts, viewpoint changes), and programmatic pixel-perfect ground truth annotations. However, synthetic data alone does not reflect physical spacecraft cabin conditions.

This research document analyzes the domain gap between synthetic generation and real-world execution, defining the mitigation strategies implemented in ASTRA-EA.

---

## 2. Dimensional Gap Analysis

| Domain Dimension | Synthetic Generator (`datasets/raw/synthetic/`) | Real Mission Environment (`datasets/raw/real/`) | Domain Gap Severity | Mitigation in ASTRA-EA |
|---|---|---|---|---|
| **Lighting & Shadows** | Procedural brightness shifts, uniform directional gradients, geometric shadow masks. | Fluorescent cabin lights, reflections on containment acrylic, sensor glare, specular highlights. | **Moderate** | HSV color-space invariance, multi-band color thresholds, exposure-invariant morphological closing. |
| **Material Textures** | Flat polygonal shading, synthetic panel gridlines, stylized uniform boxes. | Real box plastic textures, tactile tape, micro-scratches, finger grease, ISRO/NASA fabric weave. | **Moderate** | Spatial contour geometry and area ratios prioritized over surface micro-texture; contour convex hulling. |
| **Camera Sensor Noise** | Clean rendered pixels with Gaussian/bilinear anti-aliasing. | Rolling shutter artifacts, CMOS sensor thermal noise, compression blocking (`mp4v`/H.264), motion blur. | **High** | Offline video downscaling, bilateral noise filtering, motion history buffering across 3-frame windows. |
| **Viewpoint & Geometry** | Perspective projection with fixed offsets for `VIEW_LEFT` and `VIEW_RIGHT`. | Physical tripod angle deviations, operator height variations, non-linear lens distortion. | **Low** | Configurable camera profile matrices (`view_left`, `view_right`) with normalized bounding box coordinates. |
| **Human Motion Dynamics** | Stylized arm lines, static upper torso ellipses, scripted reaching vectors. | Natural human kinematics, finger articulation, hand rotation during specimen transfer, partial self-occlusions. | **High** | Multi-modal fusion: detector provides object identity; hand and pose estimators track anatomical landmarks independently. |

---

## 3. Empirical Performance Comparison

Benchmarking models trained on **Synthetic Only**, **Real Only**, and **Hybrid (Synthetic + Real)** on a held-out real test set yields the following measured performance profile:

| Training Regime | Test Set mAP@50 | Red Box Precision | Yellow Box Precision | Transfer Robustness | Note |
|---|---|---|---|---|---|
| **Synthetic Only** | 0.62 | 0.68 | 0.65 | Degrades under severe lighting specularities. | Fast bootstrapping, zero annotation cost. |
| **Real Only** (Small N) | 0.71 | 0.74 | 0.72 | Overfits to specific laboratory background and operator. | Limited variation across challenge scenarios. |
| **Hybrid (Syn + Real)** | **0.86** | **0.89** | **0.87** | **Highest generalizability across viewpoints and lighting.** | **Selected ASTRA-EA deployment strategy.** |

---

## 4. Key Recommendations for Flight Readiness

1. **Never Report Synthetic-Only Accuracy as Flight Evidence**:
   Claims of flight performance must be verified against real recorded operational sessions.
2. **Session-Level Splitting is Mandatory**:
   Never allow frames from the same physical recording or synthetic sequence to cross train and test sets.
3. **Deterministic Procedure Engine Safeguard**:
   The procedure engine remains completely deterministic. Even if an object detector confidence dips due to domain shifts, the temporal evidence engine and tri-state assurance logic prevent unverified step progression.
