# ASTRA-EA — Final Dataset Summary

## Dataset ID: `ASTRA-DATASET-v1.0`
**Freeze Status:** LOCKED & VALIDATED (Zero Cross-Split Leakage)  
**Task Domain:** Spacecraft Biological/Physical Experiment Object Interaction & Activity Recognition

---

## 1. Composition Overview

`ASTRA-DATASET-v1.0` combines live optical captures with procedurally generated synthetic microgravity interactions across controlled experimental conditions:

| Metric | Measurement | Description |
| :--- | :--- | :--- |
| **Total Labeled Frames** | `1,500+` | Curated across multiple procedural passes |
| **Active Recording Sessions** | `8` | Independent session identifiers to ensure split isolation |
| **Camera Viewpoints** | `2` | `VIEW_LEFT` (Angled lateral), `VIEW_RIGHT` (Opposed lateral) |
| **Object Classes** | `4` | `MAIN_BOX`, `RED_BOX`, `YELLOW_BOX`, `BLUE_BOX` |
| **Action Primitives** | `9` | `IDLE`, `APPROACH`, `TOUCH`, `GRASP`, `LIFT`, `HOLD`, `MOVE`, `PLACE`, `RELEASE` |
| **Composite Activities** | `4` | `PICKUP`, `MOVE_OBJECT`, `PLACE_OBJECT`, `INSPECT_OBJECT` |
| **Annotation Format** | Bounding Box + Keypoint Kinematics | YOLO-compatible normalized coordinates `[x_center, y_center, width, height]` + hand interaction flags |

---

## 2. Partitioning & Leakage Prevention

To ensure rigorous generalization, dataset partitioning is strictly enforced at the **Session Level** (never randomly shuffling adjacent frames from the same video):

* **Train Set (70%)**: Sessions `SESS_001`, `SESS_002`, `SESS_004`, `SESS_005`, `SESS_007`
* **Validation Set (15%)**: Session `SESS_003`
* **Test Set (15%)**: Sessions `SESS_006`, `SESS_008` (Locked against tuning)

### Leakage Audit Verdict
* Adjacent frame overlap between Train and Test: **0.0% (PASS)**.
* Independent background lighting and trajectory variation verified across splits.

---

## 3. Class Balance & Object Distribution

```text
Class Name        Target Function                 Train Samples    Val Samples    Test Samples
─────────────────────────────────────────────────────────────────────────────────────────────
MAIN_BOX          Experiment Containment Base     350              75             75
RED_BOX           Authorized Sample Specimen      380              80             80
YELLOW_BOX        Authorized Reagent Buffer       360              78             78
BLUE_BOX          Distractor / Deviation Object   310              65             65
```

---

## 4. Synthetic Procedural Generation

To systematically test rare edge cases, lighting drops, and camera dropouts, the Dataset Studio utilizes deterministic random seeds:
* **Generator Tool**: `core/dataset/generator.py`
* **Configured Seeds**: `10001` (Nominal), `20002` (Wrong Object), `30003` (Optical Degradation)
* **Microgravity Modeling**: Floating drift trajectories, slow non-gravitational translations, partial anatomical occlusions.
