# ==============================================================================
# ASTRA-EA Rehearsal Scenarios Definition (Phase 20, D20.06 - D20.18)
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Scenario definitions for the 12 formal operational rehearsals and dress rehearsal."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ScenarioId(str, Enum):
    """The formal operational rehearsal scenario identifiers."""
    GOLDEN_MISSION = "GOLDEN_MISSION"
    REH_01_DEVIATION = "REH_01_DEVIATION"                      # D20.07: Wrong Object Deviation & Recovery
    REH_02_CLEAN = "REH_02_CLEAN"                              # D20.06: Clean Run, Zero Deviations
    REH_03_UNCERTAINTY = "REH_03_UNCERTAINTY"                  # D20.08: Partial Occlusion & Recovery
    REH_04_NETWORK_FAILURE = "REH_04_NETWORK_FAILURE"          # D20.09: Telemetry Sever & Reconciliation
    REH_05_CAMERA_FAILURE = "REH_05_CAMERA_FAILURE"            # D20.10: Sensor Loss & Perception Pause
    REH_06_MODEL_FAILURE = "REH_06_MODEL_FAILURE"              # D20.11: Neural Exception & Fallback
    REH_07_STORAGE_WARNING = "REH_07_STORAGE_WARNING"          # D20.12: Capacity Warning & Degradation
    REH_08_GROUND_FAILURE = "REH_08_GROUND_FAILURE"            # D20.13: Ground Monitor Crash & Restart
    REH_09_VOICE_FAILURE = "REH_09_VOICE_FAILURE"              # D20.14: Audio Loss & Visual Guidance
    REH_10_COMBINED_FAULT = "REH_10_COMBINED_FAULT"            # D20.15: Dual Fault (Wrong Object + Network)
    REH_11_VIEWPOINT = "REH_11_VIEWPOINT"                      # D20.16: Multi-View (Left/Center/Right)
    REH_12_OPERATOR_INDEPENDENCE = "REH_12_OPERATOR_INDEP"     # D20.17: New Operator Independence
    DRESS_REHEARSAL = "DRESS_REHEARSAL"                        # D20.18: Final Full-Length Dress Rehearsal


@dataclass
class ScenarioMilestone:
    """Individual milestone step in an operational scenario."""
    milestone_id: str
    phase: str
    title: str
    event_type: str
    severity: str
    delay_s: float
    payload: Dict[str, Any] = field(default_factory=dict)
    ground_action_expected: Optional[str] = None


class ScenarioBuilder:
    """Constructs structured milestone sequences for all rehearsal scenarios."""

    @staticmethod
    def build(scenario_id: ScenarioId) -> List[ScenarioMilestone]:
        builder_map = {
            ScenarioId.GOLDEN_MISSION: ScenarioBuilder._build_golden_mission,
            ScenarioId.REH_01_DEVIATION: ScenarioBuilder._build_deviation_run,
            ScenarioId.REH_02_CLEAN: ScenarioBuilder._build_clean_run,
            ScenarioId.REH_03_UNCERTAINTY: ScenarioBuilder._build_uncertainty_run,
            ScenarioId.REH_04_NETWORK_FAILURE: ScenarioBuilder._build_network_run,
            ScenarioId.REH_05_CAMERA_FAILURE: ScenarioBuilder._build_camera_run,
            ScenarioId.REH_06_MODEL_FAILURE: ScenarioBuilder._build_model_run,
            ScenarioId.REH_07_STORAGE_WARNING: ScenarioBuilder._build_storage_run,
            ScenarioId.REH_08_GROUND_FAILURE: ScenarioBuilder._build_ground_run,
            ScenarioId.REH_09_VOICE_FAILURE: ScenarioBuilder._build_voice_run,
            ScenarioId.REH_10_COMBINED_FAULT: ScenarioBuilder._build_combined_run,
            ScenarioId.REH_11_VIEWPOINT: ScenarioBuilder._build_viewpoint_run,
            ScenarioId.REH_12_OPERATOR_INDEPENDENCE: ScenarioBuilder._build_operator_indep_run,
            ScenarioId.DRESS_REHEARSAL: ScenarioBuilder._build_dress_rehearsal,
        }
        builder = builder_map.get(scenario_id, ScenarioBuilder._build_golden_mission)
        return builder()

    # --------------------------------------------------------------------------
    # 1. GOLDEN MISSION / DEVIATION RUN (D20.01, D20.07)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_golden_mission() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("MS_01_PREP", "PREPARATION", "Pre-mission checklist verification", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY", "items_checked": 9}),
            ScenarioMilestone("MS_02_INIT", "INITIALIZATION", "Subsystem clock sync and frame lock", "CLOCK_INITIALIZED", "INFO", 0.05, {"met_started": True, "clock_offset_ms": 0.4}),
            ScenarioMilestone("MS_03_START", "READY", "Authorized mission start dispatched", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_GOLDEN_001", "steps": 4}),
            ScenarioMilestone("MS_04_STEP1", "EXPERIMENT", "Step 1: Approach Workstation & Stage Apparatus", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01", "confidence": 0.94}),
            ScenarioMilestone("MS_05_DEV", "ANOMALY", "Step 2: Inadvertent Wrong Apparatus Gripped (DEVIATION)", "DEVIATION_DETECTED", "WARNING", 0.1, {
                "step_id": "STEP_02", "deviation_type": "WRONG_APPARATUS", "expected": "Centrifuge Tube", "observed": "Pipette Tip Box",
                "recovery_instruction": "Return pipette box to rack; retrieve centrifuge tube."
            }, ground_action_expected="ACKNOWLEDGE_ALERT"),
            ScenarioMilestone("MS_06_REC", "RECOVERY", "Recovery guidance followed; correct apparatus detected", "RECOVERY_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02", "recovery_confirmed": True}),
            ScenarioMilestone("MS_07_STEP3", "EXPERIMENT", "Step 3: Centrifuge vortexing completed nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03", "confidence": 0.91}),
            ScenarioMilestone("MS_08_STEP4", "EXPERIMENT", "Step 4: Specimen deposition and sealing completed", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04", "confidence": 0.95}),
            ScenarioMilestone("MS_09_COMP", "COMPLETION", "Mission completed; all step assertions satisfied", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS", "deviations": 1, "recoveries": 1}),
            ScenarioMilestone("MS_10_POST", "POST_MISSION", "Post-mission audit report generation & integrity seal", "REPORT_GENERATED", "INFO", 0.05, {"sha256_verified": True}),
        ]

    @staticmethod
    def _build_deviation_run() -> List[ScenarioMilestone]:
        return ScenarioBuilder._build_golden_mission()

    # --------------------------------------------------------------------------
    # 2. CLEAN RUN (D20.06)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_clean_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("CLN_01_PREP", "PREPARATION", "Pre-mission checklist clean verification", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("CLN_02_INIT", "INITIALIZATION", "Subsystem clock sync and frame lock", "CLOCK_INITIALIZED", "INFO", 0.05, {"met_started": True}),
            ScenarioMilestone("CLN_03_START", "READY", "Authorized mission start dispatched", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_CLEAN_002", "steps": 4}),
            ScenarioMilestone("CLN_04_STEP1", "EXPERIMENT", "Step 1: Staged apparatus nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01", "confidence": 0.96}),
            ScenarioMilestone("CLN_05_STEP2", "EXPERIMENT", "Step 2: Aspirated specimen with pipette nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02", "confidence": 0.93}),
            ScenarioMilestone("CLN_06_STEP3", "EXPERIMENT", "Step 3: Centrifuge loaded and sealed nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03", "confidence": 0.95}),
            ScenarioMilestone("CLN_07_STEP4", "EXPERIMENT", "Step 4: Centrifugation cycle completed nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04", "confidence": 0.97}),
            ScenarioMilestone("CLN_08_COMP", "COMPLETION", "Experiment completed without any deviations", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS", "deviations": 0}),
            ScenarioMilestone("CLN_09_POST", "POST_MISSION", "Clean mission audit package generated", "REPORT_GENERATED", "INFO", 0.05, {"sha256_verified": True}),
        ]

    # --------------------------------------------------------------------------
    # 3. UNCERTAINTY RUN (D20.08)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_uncertainty_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("UNC_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("UNC_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_UNC_003"}),
            ScenarioMilestone("UNC_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("UNC_04_OCCL", "EXPERIMENT", "Partial visual occlusion introduced by operator sleeve", "STEP_UNCERTAIN", "NOTICE", 0.1, {
                "step_id": "STEP_02", "occlusion_ratio": 0.68, "confidence": 0.42, "reason": "PARTIAL_OCCLUSION", "false_deviation_suppressed": True
            }),
            ScenarioMilestone("UNC_05_REST", "EXPERIMENT", "Visibility restored; perception resumes confidence", "PERCEPTION_RESTORED", "INFO", 0.1, {"step_id": "STEP_02", "confidence": 0.91}),
            ScenarioMilestone("UNC_06_STEP2", "EXPERIMENT", "Step 2: Verified nominally after clearing occlusion", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("UNC_07_STEP3", "EXPERIMENT", "Step 3: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("UNC_08_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("UNC_09_COMP", "COMPLETION", "Experiment completed; uncertainty handled with zero false alarms", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 4. NETWORK FAILURE RUN (D20.09)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_network_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("NET_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("NET_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_NET_004"}),
            ScenarioMilestone("NET_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01", "sequence_num": 101}),
            ScenarioMilestone("NET_04_SEV", "ANOMALY", "Ground telemetry network link severed (LOS)", "GROUND_OFFLINE", "WARNING", 0.1, {"link_status": "OFFLINE", "onboard_mode": "AUTONOMOUS_CONTINUATION"}),
            ScenarioMilestone("NET_05_STEP2", "EXPERIMENT", "Step 2: Autonomous execution onboard proceeds without ground", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02", "sequence_num": 102, "buffered": True}),
            ScenarioMilestone("NET_06_STEP3", "EXPERIMENT", "Step 3: Autonomous execution onboard proceeds without ground", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03", "sequence_num": 103, "buffered": True}),
            ScenarioMilestone("NET_07_RECON", "RECOVERY", "Ground link restored (AOS); sequence gap reconciliation initiated", "GROUND_RECONNECTED", "INFO", 0.1, {"missed_events": [102, 103], "duplicate_count": 0}),
            ScenarioMilestone("NET_08_STEP4", "EXPERIMENT", "Step 4: Execution continues with synchronized telemetry", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04", "sequence_num": 104}),
            ScenarioMilestone("NET_09_COMP", "COMPLETION", "Experiment completed; ground state reconciled cleanly", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 5. CAMERA FAILURE RUN (D20.10)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_camera_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("CAM_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("CAM_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_CAM_005"}),
            ScenarioMilestone("CAM_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("CAM_04_FAULT", "ANOMALY", "Camera sensor stream dropped (0 fps timeout)", "CAMERA_FAILED", "CRITICAL", 0.1, {
                "subsystem": "CAMERA", "action": "VERIFICATION_PAUSED", "allow_step_verification": False
            }),
            ScenarioMilestone("CAM_05_RESTORE", "RECOVERY", "Camera sensor bus re-enumerated and restored", "CAMERA_RESTORED", "INFO", 0.1, {"fps": 30.0, "perception_resumed": True}),
            ScenarioMilestone("CAM_06_STEP2", "EXPERIMENT", "Step 2: Step verification resumes only with valid optical frames", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("CAM_07_STEP3", "EXPERIMENT", "Step 3: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("CAM_08_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("CAM_09_COMP", "COMPLETION", "Experiment completed safely without unverified transitions", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 6. MODEL FAILURE RUN (D20.11)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_model_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("MOD_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("MOD_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_MOD_006"}),
            ScenarioMilestone("MOD_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("MOD_04_ERR", "ANOMALY", "Neural model inference execution exception caught", "MODEL_FAILURE", "WARNING", 0.1, {
                "error": "ONNX_RUNTIME_EXCEPTION", "fallback_engaged": "RULE_BASED_HEURISTIC"
            }),
            ScenarioMilestone("MOD_05_STEP2", "EXPERIMENT", "Step 2: Execution sustained via validated rule fallback", "STEP_VERIFIED", "NOTICE", 0.1, {"step_id": "STEP_02", "detector": "FALLBACK"}),
            ScenarioMilestone("MOD_06_STEP3", "EXPERIMENT", "Step 3: Verified via fallback", "STEP_VERIFIED", "NOTICE", 0.1, {"step_id": "STEP_03", "detector": "FALLBACK"}),
            ScenarioMilestone("MOD_07_STEP4", "EXPERIMENT", "Step 4: Verified via fallback", "STEP_VERIFIED", "NOTICE", 0.1, {"step_id": "STEP_04", "detector": "FALLBACK"}),
            ScenarioMilestone("MOD_08_COMP", "COMPLETION", "Experiment completed under graceful model degradation", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 7. STORAGE WARNING RUN (D20.12)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_storage_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("STO_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("STO_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_STO_007"}),
            ScenarioMilestone("STO_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("STO_04_WARN", "ANOMALY", "Storage partition utilization crossed 88% threshold", "STORAGE_WARNING", "WARNING", 0.1, {
                "utilization_pct": 88.5, "policy": "PRUNE_NON_CRITICAL_DEBUG_FRAMES", "critical_evidence_preserved": True
            }),
            ScenarioMilestone("STO_05_STEP2", "EXPERIMENT", "Step 2: Storage policy pruned debug logs; continued safely", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("STO_06_STEP3", "EXPERIMENT", "Step 3: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("STO_07_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("STO_08_COMP", "COMPLETION", "Experiment completed; retention policy successfully maintained margin", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 8. GROUND FAILURE RUN (D20.13)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_ground_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("GND_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("GND_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_GND_008"}),
            ScenarioMilestone("GND_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("GND_04_CRASH", "ANOMALY", "Ground monitor UI process terminated abruptly (SIGKILL)", "GROUND_CRASHED", "WARNING", 0.1, {"onboard_unaffected": True}),
            ScenarioMilestone("GND_05_STEP2", "EXPERIMENT", "Step 2: Onboard runtime continues without ground monitor", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("GND_06_RESTART", "RECOVERY", "Ground monitor process restarted by ground operator", "GROUND_RECONNECTED", "INFO", 0.1, {"reconstructed_state": "RUNNING", "current_step": "STEP_03"}),
            ScenarioMilestone("GND_07_STEP3", "EXPERIMENT", "Step 3: Ground observability active again", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("GND_08_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("GND_09_COMP", "COMPLETION", "Experiment completed; ground monitor state rebuilt faithfully", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 9. VOICE FAILURE RUN (D20.14)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_voice_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("VOI_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("VOI_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_VOI_009"}),
            ScenarioMilestone("VOI_03_STEP1", "EXPERIMENT", "Step 1: Audio synthesizer driver failure", "VOICE_FAILED", "NOTICE", 0.1, {"audio_device": "UNAVAILABLE", "visual_guidance": "ACTIVE"}),
            ScenarioMilestone("VOI_04_STEP2", "EXPERIMENT", "Step 2: Operator completes action following visual HUD prompts", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("VOI_05_STEP3", "EXPERIMENT", "Step 3: Visual guidance remains fully responsive", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("VOI_06_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("VOI_07_COMP", "COMPLETION", "Experiment completed safely despite audio subsystem outage", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 10. COMBINED FAULT RUN (D20.15)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_combined_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("CMB_01_PREP", "PREPARATION", "Pre-mission checks passed", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("CMB_02_START", "READY", "Experiment started", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_CMB_010"}),
            ScenarioMilestone("CMB_03_STEP1", "EXPERIMENT", "Step 1: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("CMB_04_NET_LOSS", "ANOMALY", "Telemetry link severed during step transition", "GROUND_OFFLINE", "WARNING", 0.1, {"link": "OFFLINE"}),
            ScenarioMilestone("CMB_05_WRONG_OBJ", "ANOMALY", "Operator simultaneously grasps wrong apparatus", "DEVIATION_DETECTED", "WARNING", 0.1, {
                "step_id": "STEP_02", "deviation_type": "WRONG_APPARATUS", "onboard_audio_guidance": "ACTIVE"
            }),
            ScenarioMilestone("CMB_06_REC_ONBOARD", "RECOVERY", "Operator corrects apparatus following onboard HUD/voice", "RECOVERY_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02"}),
            ScenarioMilestone("CMB_07_NET_RECONN", "RECOVERY", "Ground link restored; deviation and recovery reconciled to ground", "GROUND_RECONNECTED", "INFO", 0.1, {"reconciled_events": 2}),
            ScenarioMilestone("CMB_08_STEP3", "EXPERIMENT", "Step 3: Execution continues synchronized", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("CMB_09_STEP4", "EXPERIMENT", "Step 4: Verified normally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("CMB_10_COMP", "COMPLETION", "Experiment completed; combined fault recovered with zero corruption", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 11. VIEWPOINT RUN (D20.16)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_viewpoint_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("VIEW_01_PREP", "PREPARATION", "Multi-view optical calibration validated", "PRECHECK_COMPLETED", "INFO", 0.05, {"views": ["VIEW_LEFT", "VIEW_CENTER", "VIEW_RIGHT"]}),
            ScenarioMilestone("VIEW_02_START", "READY", "Multi-view procedure initiated", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_VIEW_011"}),
            ScenarioMilestone("VIEW_03_LEFT", "EXPERIMENT", "VIEW_LEFT: Primary angle evaluates step 1", "STEP_VERIFIED", "INFO", 0.1, {"view": "VIEW_LEFT", "confidence": 0.94}),
            ScenarioMilestone("VIEW_04_CENTER", "EXPERIMENT", "VIEW_CENTER: Intermediate verification confirms apparatus alignment", "STEP_VERIFIED", "INFO", 0.1, {"view": "VIEW_CENTER", "confidence": 0.92}),
            ScenarioMilestone("VIEW_05_RIGHT", "EXPERIMENT", "VIEW_RIGHT: High-angle confirms centrifugation seating", "STEP_VERIFIED", "INFO", 0.1, {"view": "VIEW_RIGHT", "confidence": 0.95}),
            ScenarioMilestone("VIEW_06_STEP4", "EXPERIMENT", "Step 4: Multi-view cross-validation satisfied", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04", "consensus": True}),
            ScenarioMilestone("VIEW_07_COMP", "COMPLETION", "Procedure completed with 100% viewpoint decision consistency", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
        ]

    # --------------------------------------------------------------------------
    # 12. OPERATOR INDEPENDENCE RUN (D20.17)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_operator_indep_run() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("IND_01_MANUAL", "PREPARATION", "New operator consults docs/operations/operator-manual.md without developer assistance", "MANUAL_READ", "INFO", 0.05, {"operator": "Trainee_Astronaut_B"}),
            ScenarioMilestone("IND_02_PRECHECK", "PREPARATION", "Operator executes 'astra mission precheck' independently", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY"}),
            ScenarioMilestone("IND_03_START", "READY", "Operator authorizes experiment start via Mission Console", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_INDEP_012"}),
            ScenarioMilestone("IND_04_STEP1", "EXPERIMENT", "Operator executes Step 1", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01"}),
            ScenarioMilestone("IND_05_DEV", "ANOMALY", "Planned deviation injected; system alerts new operator", "DEVIATION_DETECTED", "WARNING", 0.1, {"alert_acknowledged_by_operator": True}),
            ScenarioMilestone("IND_06_REC", "RECOVERY", "New operator follows standard recovery playbook; recovers correctly", "RECOVERY_VERIFIED", "INFO", 0.1, {"recovery_time_s": 3.8}),
            ScenarioMilestone("IND_07_STEP3", "EXPERIMENT", "Operator continues remaining steps independently", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03"}),
            ScenarioMilestone("IND_08_STEP4", "EXPERIMENT", "Final step executed and verified", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04"}),
            ScenarioMilestone("IND_09_COMP", "COMPLETION", "Mission completed successfully with zero developer interventions", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS", "developer_interventions": 0}),
        ]

    # --------------------------------------------------------------------------
    # 13. DRESS REHEARSAL (D20.18, Section 46-49)
    # --------------------------------------------------------------------------
    @staticmethod
    def _build_dress_rehearsal() -> List[ScenarioMilestone]:
        return [
            ScenarioMilestone("DR_01_T_START", "PREPARATION", "T-START: Clean operational environment initialized", "PRECHECK_COMPLETED", "INFO", 0.05, {"verdict": "READY", "env": "FLIGHT_LIKE"}),
            ScenarioMilestone("DR_02_CHECKLIST", "PREPARATION", "All 9 pre-mission checklist categories explicitly signed off", "CHECKLIST_SIGNED", "INFO", 0.05, {"checklist_id": "PRE_MISSION"}),
            ScenarioMilestone("DR_03_SELFTEST", "INITIALIZATION", "Subsystem health self-test & clock lock", "CLOCK_INITIALIZED", "INFO", 0.05, {"health": "NOMINAL"}),
            ScenarioMilestone("DR_04_DISPATCH", "READY", "Mission supervisor authorizes experiment commencement", "EXPERIMENT_STARTED", "INFO", 0.05, {"run_id": "RUN_DRESS_REHEARSAL_FINAL"}),
            ScenarioMilestone("DR_05_STEP1", "EXPERIMENT", "Step 1: Staged apparatus verified via neural detection", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_01", "confidence": 0.95}),
            ScenarioMilestone("DR_06_PLANNED_DEV", "ANOMALY", "Step 2: Planned intentional wrong apparatus deviation flagged", "DEVIATION_DETECTED", "WARNING", 0.1, {
                "step_id": "STEP_02", "deviation_type": "WRONG_APPARATUS", "recovery_guidance": "Return pipette box to rack; retrieve centrifuge tube."
            }, ground_action_expected="ACKNOWLEDGE_ALERT"),
            ScenarioMilestone("DR_07_PLANNED_REC", "RECOVERY", "Recovery guidance followed; physical correction verified", "RECOVERY_VERIFIED", "INFO", 0.1, {"step_id": "STEP_02", "verified": True}),
            ScenarioMilestone("DR_08_STEP3", "EXPERIMENT", "Step 3: Centrifuge vortexing completed nominally", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_03", "confidence": 0.92}),
            ScenarioMilestone("DR_09_STEP4", "EXPERIMENT", "Step 4: Final specimen deposition completed and sealed", "STEP_VERIFIED", "INFO", 0.1, {"step_id": "STEP_04", "confidence": 0.96}),
            ScenarioMilestone("DR_10_COMPLETE", "COMPLETION", "Experiment completed; all procedure assertions satisfied", "EXPERIMENT_COMPLETED", "INFO", 0.05, {"status": "SUCCESS"}),
            ScenarioMilestone("DR_11_POST", "POST_MISSION", "Post-mission records finalized, checksums calculated, report generated", "REPORT_GENERATED", "INFO", 0.05, {"integrity": "PASS"}),
            ScenarioMilestone("DR_12_GROUND_REV", "POST_MISSION", "Ground review completed; zero source code changes or developer interventions", "GROUND_REVIEW_COMPLETED", "INFO", 0.05, {"developer_interventions": 0}),
        ]
