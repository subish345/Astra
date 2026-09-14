"""Step Evaluator (D4.03) for ASTRA-EA.

Evaluates StepCandidate hypotheses against multimodal EvidenceBundles and
configured ExperimentStep criteria to determine VERIFIED, UNCERTAIN, or NOT_MATCHED status.
Strictly leaves final DEVIATION classification to Phase 5.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.evidence.types import EvidenceBundle
from core.procedure.schema import ExperimentStep
from core.procedure.types import StepCandidate, StepEvaluation, StepMatchStatus


class StepEvaluator:
    """Combines candidate matching and multimodal evidence to evaluate step satisfaction."""

    def __init__(
        self,
        uncertain_threshold_ratio: float = 0.65,
        default_procedure_version: str = "1.0.0",
        default_model_version: str = "yolov8n-custom-0.1",
        default_software_version: str = "0.4.0",
    ):
        self.uncertain_threshold_ratio = uncertain_threshold_ratio
        self.default_procedure_version = default_procedure_version
        self.default_model_version = default_model_version
        self.default_software_version = default_software_version

    def evaluate_step(
        self,
        candidate: StepCandidate,
        bundle: EvidenceBundle,
        step: ExperimentStep,
        experiment_id: str = "DEMO_EXP_001",
        run_id: str = "RUN_001",
        procedure_version: Optional[str] = None,
        model_version: Optional[str] = None,
        software_version: Optional[str] = None,
    ) -> StepEvaluation:
        """Produce a formal StepEvaluation for a candidate and its supporting evidence."""
        reasons: List[str] = []

        # 1. Check candidate-step identity
        if candidate.step_id != step.id:
            return StepEvaluation(
                experiment_id=experiment_id,
                run_id=run_id,
                step_id=step.id,
                status=StepMatchStatus.NOT_MATCHED,
                confidence=0.0,
                evidence_bundle_id=bundle.bundle_id,
                timestamp_start=candidate.timestamp_start,
                timestamp_end=candidate.timestamp_end,
                source_activity_ids=[candidate.activity_id] if candidate.activity_id else [],
                reasons=[f"Candidate step {candidate.step_id} does not match target step {step.id}"],
                procedure_version=procedure_version or self.default_procedure_version,
                model_version=model_version or self.default_model_version,
                software_version=software_version or self.default_software_version,
            )

        # 2. Minimum duration check
        duration = max(0.0, candidate.timestamp_end - candidate.timestamp_start)
        duration_satisfied = True
        if step.min_duration_seconds > 0.0 and duration < step.min_duration_seconds:
            duration_satisfied = False
            reasons.append(
                f"Observed duration {duration:.2f}s is below required {step.min_duration_seconds:.2f}s"
            )

        # 3. Required evidence check
        req_satisfied = bundle.required_satisfied
        if not req_satisfied:
            reasons.append(f"Missing required evidence: {bundle.missing_required}")

        # 4. Action sequence check (Prompt §9)
        action_seq_satisfied = True
        observed_actions: List[str] = []
        if step.action_sequence:
            cand_act = candidate.activity_type.upper().strip()
            match_details = candidate.match_details or {}
            observed_actions = [str(a).upper().strip() for a in match_details.get("primitives", [])]
            if cand_act not in observed_actions:
                observed_actions.append(cand_act)
            expected_sequence = [a.upper().strip() for a in step.action_sequence]
            observed_iter = iter(observed_actions)
            if not all(any(observed == expected for observed in observed_iter) for expected in expected_sequence):
                action_seq_satisfied = False
                reasons.append(
                    f"Action sequence incomplete: observed {observed_actions}, expected {step.action_sequence}"
                )

        # 5. Confidence thresholds
        target_min_conf = step.min_confidence
        composite_conf = (bundle.evidence_score * 0.60) + (candidate.match_score * 0.40)
        conf_satisfied = composite_conf >= target_min_conf
        if not conf_satisfied:
            reasons.append(
                f"Confidence {composite_conf:.2f} is below step minimum {target_min_conf:.2f}"
            )

        # 6. Determine StepMatchStatus (VERIFIED, UNCERTAIN, NOT_MATCHED)
        # Fast-placement demo rule: entering the virtual work surface is the
        # completion trigger, even with a small or moving box.
        fast_virtual_place = (
            step.id == "STEP_03"
            and getattr(step, "allow_unstable_placement", False)
            and bundle.check_requirement("DESTINATION_MATCH")
        )
        if fast_virtual_place:
            status = StepMatchStatus.VERIFIED
            reasons.append("Virtual work-surface placement accepted (fast demo rule)")
        elif req_satisfied and conf_satisfied and duration_satisfied and action_seq_satisfied:
            status = StepMatchStatus.VERIFIED
            reasons.append("All required evidence, confidence threshold, and temporal constraints satisfied")
        elif (
            composite_conf >= (target_min_conf * self.uncertain_threshold_ratio)
            or (len(bundle.missing_required) <= 1 and composite_conf >= 0.45)
        ):
            status = StepMatchStatus.UNCERTAIN
            reasons.append("Partial evidence corroboration observed, insufficient for definitive verification")
        else:
            status = StepMatchStatus.NOT_MATCHED
            reasons.append("Insufficient evidence or confidence to corroborate step")

        metadata: Dict[str, Any] = {
            "required_satisfied": req_satisfied,
            "missing_required": bundle.missing_required,
            "action_sequence_satisfied": action_seq_satisfied,
            "expected_action_sequence": step.action_sequence,
            "observed_actions": observed_actions,
            "evidence_score": bundle.evidence_score,
            "candidate_match_score": candidate.match_score,
            "composite_confidence": round(composite_conf, 3),
            "duration_seconds": round(duration, 3),
            "step_min_confidence": target_min_conf,
            "bundle_items_verified": [k for k, v in bundle.items.items() if v.verified],
        }

        return StepEvaluation(
            experiment_id=experiment_id,
            run_id=run_id,
            step_id=step.id,
            status=status,
            confidence=round(composite_conf, 3),
            evidence_bundle_id=bundle.bundle_id,
            timestamp_start=candidate.timestamp_start,
            timestamp_end=candidate.timestamp_end,
            source_activity_ids=[candidate.activity_id] if candidate.activity_id else [],
            procedure_version=procedure_version or self.default_procedure_version,
            model_version=model_version or self.default_model_version,
            software_version=software_version or self.default_software_version,
            reasons=reasons,
            metadata=metadata,
        )
