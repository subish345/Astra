# Dataset Card: ASTRA-DATASET-v1.0

**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Dataset Identifier:** `ASTRA-DATASET-v1.0`  
**License:** Research / Ground Demonstration Only  
**Release Date:** 2026-09-13  
**Status:** **FROZEN (Zero post-benchmark alterations permitted)**

---

## 1. Dataset Summary & Scope
`ASTRA-DATASET-v1.0` is a curated, domain-specific multi-modal vision dataset engineered specifically for fine-grained object detection, hand-object interaction estimation, and procedure verification during astronaut laboratory experiments.

It addresses the fundamental limitations of generic Human Activity Recognition (HAR) datasets by pairing high-resolution spatial annotations with temporal state-transition milestones.

---

## 2. Dataset Composition & Split Statistics

- **Total Frames:** 8,420 annotated frames across 42 recording sessions.
- **Physical Laboratory Video:** 4,620 frames (54.9%) recorded under physical laboratory setups.
- **Parametric Synthetic Variations:** 3,800 frames (45.1%) generated through procedural illumination and viewpoint rendering.

### Partition Splits
| Partition | Frame Count | Percentage | Integrity Hash Status |
| :--- | :---: | :---: | :--- |
| **Train** | 5,894 | 70.0% | Verified |
| **Validation** | 1,263 | 15.0% | Verified |
| **Test** | 1,263 | 15.0% | **LOCKED & FROZEN** |
| **Total** | **8,420** | **100.0%** | SHA-256 Verified |

*Zero train/test leakage: The test partition contains strictly independent physical and synthetic recording sessions unseen during model optimization.*

---

## 3. Class Distribution & Spatial Annotations
Bounding box annotations follow standard YOLO / Pascal VOC format `[class_id, x_center, y_center, width, height]` normalized to $[0.0, 1.0]$.

| Class Name | Target Object Type | Annotation Count | Proportion |
| :--- | :--- | :---: | :---: |
| `specimen_tube` | Biological sample container | 3,140 | 28.2% |
| `centrifuge_tube` | Conical centrifuge vial | 2,820 | 25.3% |
| `pipette` | Micropipette dispensing tool | 2,410 | 21.6% |
| `petri_dish` | Cell culture glass dish | 1,120 | 10.1% |
| `tube_rack` | Workspace storage rack | 980 | 8.8% |
| `chemical_vial` | Reagent reservoir bottle | 670 | 6.0% |

---

## 4. Multi-Angle Viewpoint Variations
Data collection was structured across multiple spatial perspectives to ensure viewpoint invariance:
- **Lateral Left (`VIEW_LEFT`):** $40^\circ$ oblique overhead perspective (primary demonstration baseline).
- **Lateral Right (`VIEW_RIGHT`):** $40^\circ$ mirror perspective for contact topology verification.
- **Top-Down (`VIEW_TOP`):** $90^\circ$ planar overhead perspective for workspace zone boundary tracking.

---

## 5. Synthetic Data Engineering & Domain Gap Disclosures
- **Why Synthetic:** Extreme laboratory failure modes (e.g. spilled bio-agents, shattered glassware, severe solar flare reflections) occur too infrequently in physical laboratory sessions to train robust anomaly detectors.
- **Parametric Controls:** The synthetic generator systematically varied ambient light between 15 and 400 Lux, applied rotational jitter ($\pm 30^\circ$), and randomly injected anomalous object grasps.
- **Known Domain Gap:** Procedurally rendered textures cannot fully replicate non-rigid glove wrinkling or microscopic liquid meniscus curvature in transparent glass. Physical testing on 4,620 real frames bridges this gap.
