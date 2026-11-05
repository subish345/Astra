# ASTRA-EA — Multimodal Evidence Engine Architecture

## 1. Overview & Principles

AI model confidence cannot serve as mission ground truth in human spaceflight operations. In ASTRA-EA, confidence from object detection, pose estimation, and activity recognition is corroborated across independent physical and temporal dimensions to produce explainable, traceable **Evidence Bundles**.

$$\text{Perception Confidence} + \text{Interaction Evidence} + \text{Temporal Consistency} + \text{Procedure Match} = \text{Step Assurance Evidence}$$

---

## 2. Evidence Taxonomy (13 Dimensions)

Defined in [`core/evidence/types.py`](file:///home/subish-loq/Documents/astra/core/evidence/types.py):

| Evidence Type | Verification Criterion | Source Modality |
|---|---|---|
| `OBJECT_DETECTED` | Target experiment object track is active and visible | Object Detector & MultiObjectTracker |
| `ASTRONAUT_DETECTED` / `ACTOR_DETECTED` | Human crew member detected in workstation volume | LightweightPoseEstimator |
| `HAND_DETECTED` | Left or right hand landmark observed | LightweightHandDetector |
| `HAND_OBJECT_CONTACT` | Euclidean distance between wrist/centroid and object bounding box $\le 0.18$ | SpatialInteractionEngine |
| `OBJECT_MOTION` | Object centroid velocity $\ge 12.0\text{ px/s}$ across sliding observation window | MultiObjectTracker & TemporalBuffer |
| `HAND_MOTION` | Hand keypoint centroid displacement velocity exceeds minimum threshold | TemporalBuffer |
| `COUPLED_MOTION` | Simultaneous hand contact and object motion with correlated trajectory | Interaction & Kinematics |
| `POSE_CONSISTENCY` | Keypoint visibility and biomechanical joint angle validity | Pose Estimator |
| `SPATIAL_RELATIONSHIP` | Directional alignment and overlap IoU between hand and object | Spatial Analysis |
| `TEMPORAL_CONSISTENCY` | Action duration satisfies $[\text{min\_duration}, \text{timeout}]$ bounds | Temporal Buffer |
| `ACTIVITY_CONFIRMED` | Activity recognition confidence exceeds confidence tier | Activity Engine |
| `PROCEDURE_MATCH` | Action primitive and target object match procedure definition | Procedure Matcher |
| `DESTINATION_MATCH` | Moved object enters designated recipient container / work surface | Spatial Geometry |

---

## 3. Deterministic Evidence Scoring Formulation

Evidence scoring is deterministic, explainable, and unit-tested:

$$\text{Score} = w_r \cdot R_{\text{req}} + w_c \cdot C_{\text{mean}} + w_t \cdot S_{\text{temporal}} + w_p \cdot S_{\text{procedure}}$$

Where:
* $w_r = 0.40$ (Required evidence satisfaction ratio: $1.0 - \frac{\text{missing}}{\text{total\_required}}$)
* $w_c = 0.25$ (Mean confidence across all observed evidence items)
* $w_t = 0.15$ (Temporal duration consistency factor)
* $w_p = 0.20$ (Procedure compatibility score from Procedure Matcher)

---

## 4. Alternate Evidence Path Groupings

Experiment procedures can define flexible, non-brittle evidence rules via [`EvidencePathRule`](file:///home/subish-loq/Documents/astra/core/procedure/schema.py):

```yaml
evidence_paths:
  any_of:
    - ["object_visible", "hand_visible", "contact_detected"]
    - ["OBJECT_DETECTED", "COUPLED_MOTION"]
```

Supported evaluation operators:
* `all_of`: All listed evidence flags must be verified.
* `any_of`: At least one sub-list group of evidence items must be verified.
* `one_of`: Exactly one of the specified evidence flags must be satisfied.

---

## 5. Causal Audit Traceability

Every [`StepEvaluation`](file:///home/subish-loq/Documents/astra/core/procedure/types.py) retains an unbroken causal chain:

```text
STEP_02: Grasp Specimen Red Box [VERIFIED - 93.00%]
├── Candidate Action: GRASP (match: 0.94) on RED_BOX
├── Activity Concept: GRASP (duration: 2.00s, frames: 100–160)
├── Interaction: RIGHT_HAND -> RED_BOX (distance: 0.04)
├── Track ID: #2 (RED_BOX, confidence: 0.95)
├── Evidence Bundle EVD_369DD340:
│   ├── ✓ OBJECT_DETECTED (conf: 0.95)
│   ├── ✓ HAND_DETECTED (conf: 0.92)
│   ├── ✓ HAND_OBJECT_CONTACT (conf: 0.90)
│   └── ✓ TEMPORAL_CONSISTENCY (conf: 0.90)
└── Audit Decision: All required evidence, duration, and thresholds satisfied
```
