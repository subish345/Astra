# Temporal Activity Recognition Architecture (Phase 3)

## 1. Hierarchy of Understanding
The Activity Recognition Subsystem (`core/activity/`) operates over a bounded rolling temporal window, transforming fine-grained physical interaction events into structured human activities.

```text
InteractionEvent Stream (Per-frame physical coupling)
           │
           ▼
Rolling Temporal Buffer (Bounded ring buffer: 5.0s window)
           │
           ▼
Temporal Feature Extractor (Velocity, Acceleration, Contact Duration, Relative Motion)
           │
           ▼
Primitive Activity Engine (IDLE, APPROACH, TOUCH, GRASP, LIFT, HOLD, MOVE, PLACE, RELEASE)
           │
           ▼
Composite Activity Engine (PICKUP, MOVE_OBJECT, PLACE_OBJECT)
           │
           ▼
Explainable Confidence & Uncertainty Handler (HIGH, MEDIUM, LOW, UNKNOWN)
           │
           ▼
Deduplicated Activity Telemetry & Annotation Pipeline
```

---

## 2. Activity Categories

### 2.1 Primitive Activities
- `IDLE`: Hand stationary, outside interaction proximity.
- `APPROACH`: Hand closing distance towards object over multiple frames.
- `TOUCH`: Physical contact established without significant displacement.
- `GRASP`: Stable contact confirmed with posture coupling.
- `LIFT`: Vertical translation following grasp ($\Delta y < -30$ pixels in frame coordinates).
- `HOLD`: Object stationary while sustained contact is maintained.
- `MOVE`: Coupled translation across the workspace.
- `PLACE`: Object decelerates to stationary at a destination surface.
- `RELEASE`: Hand separates and departs from object.

### 2.2 Composite Activities
- `PICKUP`: Sequence of `[APPROACH -> TOUCH/GRASP -> LIFT]`.
- `MOVE_OBJECT`: Sequence of `[HOLD -> MOVE]`.
- `PLACE_OBJECT`: Sequence of `[MOVE -> PLACE -> RELEASE]`.

> [!NOTE]
> All composite activities retain the underlying list of constituent primitive activities (`primitives`) and temporal bounds (`TemporalWindow`) for full auditability by the Phase 4 Evidence Engine.

---

## 3. Explainable Confidence Formulation

Activity confidence is computed from multiple independent physical signals rather than fabricated heuristic constants:

$$C_{\text{activity}} = w_{\text{obj}} C_{\text{obj}} + w_{\text{hand}} C_{\text{hand}} + w_{\text{cont}} C_{\text{cont}} + w_{\text{mot}} C_{\text{mot}} + w_{\text{temp}} C_{\text{temp}}$$

Default calibration weights:
- $w_{\text{obj}} = 0.20$ (Object detector confidence)
- $w_{\text{hand}} = 0.20$ (Hand detector landmark confidence)
- $w_{\text{cont}} = 0.25$ (Contact persistence and IoU overlap)
- $w_{\text{mot}} = 0.20$ (Cosine motion correlation $\cos \theta$)
- $w_{\text{temp}} = 0.15$ (Temporal duration relative to minimum threshold)

### Qualitative Tiers
- $\ge 0.80 \to \text{HIGH}$
- $\ge 0.60 \to \text{MEDIUM}$
- $\ge 0.40 \to \text{LOW}$
- $< 0.40 \to \text{UNKNOWN}$
