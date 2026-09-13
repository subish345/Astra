# ASTRA-EA — Evidence Operations & Review Guide

## Phase 19: Mission Operations & Ground Segment Integration (D19.12)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Evidence Architecture & Chain of Custody (Section 34)

In safety-critical space missions, every assurance decision made by ASTRA-EA must be auditable. ASTRA-EA produces an immutable, cryptographically verifiable evidence trail for:
1. Every step verification (`STEP_VERIFIED`).
2. Every ambiguous action (`STEP_UNCERTAIN`).
3. Every protocol violation (`DEVIATION_DETECTED`).
4. Every corrective action (`RECOVERY_VERIFIED`).

---

## 2. Evidence Package Data Structure (Section 34)

Each evidence record stored in `flight_data/evidence/` contains:

```json
{
  "evidence_id": "EVID_RUN_0001_STEP_02_DEV",
  "run_id": "RUN_0001",
  "step_id": "STEP_02",
  "event_id": "EVT_00012",
  "onboard_met_seconds": 45.120,
  "timestamp_utc": "2026-09-13T14:22:15.120Z",
  "decision": "DEVIATION",
  "detected_objects": [
    {
      "class_name": "pipette_box",
      "confidence": 0.94,
      "bounding_box": [140, 220, 260, 340]
    }
  ],
  "hand_pose": {
    "left_hand_active": false,
    "right_hand_grasp": true,
    "interaction_zone": "STAGE_AREA_LEFT"
  },
  "snapshot_path": "evidence/EVID_RUN_0001_STEP_02_DEV.jpg",
  "video_clip_path": "evidence/EVID_RUN_0001_STEP_02_DEV.mp4",
  "sha256": "41a60230257db9f..."
}
```

---

## 3. Evidence Review Workflow (Section 32, 33)

Ground scientists and principal investigators review evidence using:

1. **Mission Console Evidence Panel:** Click on any past timeline event to view associated video clip and object bounding boxes.
2. **Ground Monitor Evidence Dialog:** Double-click any milestone on the timeline to pop up the `EvidenceViewerDialog`.
3. **CLI Review Command:**
   ```bash
   astra mission review --run RUN_0001
   ```
4. **Exported HTML Report:** Open `reports/mission_report_RUN_0001.html` in any browser to inspect full timeline and deviation logs.
