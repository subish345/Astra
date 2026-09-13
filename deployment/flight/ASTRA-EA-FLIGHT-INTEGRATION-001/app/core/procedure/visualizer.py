"""Procedure Debug Visualizer (D4.08) for ASTRA-EA.

Renders high-visibility procedural step progression, active evidence checklists,
and candidate evaluation telemetry onto both terminal consoles and OpenCV video frames.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from core.evidence.types import EvidenceBundle
from core.procedure.schema import ExperimentDefinition, ExperimentStep
from core.procedure.types import ProcedureState, ProcedureStatus, StepEvaluation, StepMatchStatus


class ProcedureVisualizer:
    """Developer interface and telemetry renderer for experiment procedure reasoning."""

    # UI Color palette (BGR for OpenCV)
    COLOR_VERIFIED = (80, 220, 80)     # Emerald Green
    COLOR_CURRENT = (0, 215, 255)      # Amber / Gold
    COLOR_UNCERTAIN = (40, 160, 255)   # Orange
    COLOR_PENDING = (150, 150, 150)    # Slate Gray
    COLOR_BG = (16, 18, 22)            # Dark Space Slate
    COLOR_BORDER = (60, 70, 85)        # Frame Border
    COLOR_TEXT = (230, 235, 240)       # Clean White

    def __init__(self, procedure: ExperimentDefinition):
        self.procedure = procedure
        self._step_map: Dict[str, ExperimentStep] = {s.id: s for s in procedure.steps}

    def render_terminal_monitor(
        self,
        state: ProcedureState,
        bundle: Optional[EvidenceBundle] = None,
        evaluation: Optional[StepEvaluation] = None,
    ) -> str:
        """Format an ASCII developer monitor view of the current procedure execution."""
        lines = [
            "=" * 60,
            f"EXPERIMENT: {self.procedure.experiment.name} ({self.procedure.experiment.id} v{self.procedure.experiment.version})",
            f"RUN ID:     {state.run_id} | STATUS: {state.procedure_status.value}",
            "-" * 60,
            "PROCEDURE TIMELINE:",
        ]

        for step in sorted(self.procedure.steps, key=lambda s: s.sequence):
            if step.id in state.completed_steps:
                icon = "✓"
                tag = "COMPLETED"
            elif step.id == state.current_step:
                icon = "●"
                tag = "CURRENT"
            elif step.id == state.uncertain_step:
                icon = "?"
                tag = "UNCERTAIN"
            else:
                icon = "○"
                tag = "PENDING"
            lines.append(f"  {icon} {step.id} [{step.sequence}]: {step.name:<24} [{tag}]")

        lines.append("-" * 60)
        curr_step_id = state.current_step or "NONE"
        curr_step = self._step_map.get(curr_step_id)

        exp_act = ", ".join(curr_step.expected_actions) if curr_step else "NONE"
        exp_obj = ", ".join(curr_step.expected_objects) if curr_step else "NONE"

        lines.append(f"CURRENT STEP:     {curr_step_id}")
        lines.append(f"EXPECTED ACTION:  {exp_act} -> {exp_obj}")

        if bundle:
            lines.append(f"OBSERVED ACT:     {bundle.activity_name} on {bundle.target_object_id or 'NONE'}")
            lines.append(f"EVIDENCE SCORE:   {bundle.evidence_score:.2f} (Required: {'PASS' if bundle.required_satisfied else 'FAIL'})")
            ev_summary = []
            for k, it in bundle.items.items():
                m = "✓" if it.verified else "✗"
                ev_summary.append(f"{m}{k.split('_')[0]}")
            lines.append(f"EVIDENCE ITEMS:   {' '.join(ev_summary)}")

        if evaluation:
            lines.append(f"STEP DECISION:    {evaluation.status.value} (conf: {evaluation.confidence:.2%})")

        next_str = state.next_expected_step or "NONE (PROCEDURE COMPLETE)"
        lines.append(f"NEXT EXPECTED:    {next_str}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def draw_procedure_hud(
        self,
        frame: np.ndarray,
        state: ProcedureState,
        bundle: Optional[EvidenceBundle] = None,
        evaluation: Optional[StepEvaluation] = None,
        camera_profile: Optional[str] = None,
        assurance_decision: Optional[Any] = None,
        recovery_state: Optional[str] = None,
    ) -> np.ndarray:
        """Render a semi-transparent procedural monitor panel onto an OpenCV frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # Procedure HUD panel on top right
        panel_w = 300
        panel_h = min(420, h - 24)
        px = w - panel_w - 12
        py = 12

        overlay = vis.copy()
        cv2.rectangle(overlay, (px, py), (px + panel_w, py + panel_h), self.COLOR_BG, -1)
        cv2.rectangle(overlay, (px, py), (px + panel_w, py + panel_h), self.COLOR_BORDER, 1)
        cv2.addWeighted(overlay, 0.84, vis, 0.16, 0, vis)

        ty = py + 20
        # Title
        cv2.putText(vis, "ASSURANCE MONITOR", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1, cv2.LINE_AA)
        ty += 16

        # Camera Profile (Prompt Section 4)
        cam_prof_str = camera_profile or "VIEW_LEFT"
        cv2.putText(vis, f"Camera Profile: {cam_prof_str.upper()}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80, 210, 255), 1, cv2.LINE_AA)
        ty += 16
        cv2.putText(vis, f"EXP: {self.procedure.experiment.id}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 190, 200), 1)
        ty += 14
        cv2.line(vis, (px + 8, ty - 6), (px + panel_w - 8, ty - 6), self.COLOR_BORDER, 1)

        # Timeline
        for step in sorted(self.procedure.steps, key=lambda s: s.sequence):
            is_done = step.id in state.completed_steps
            is_curr = step.id == state.current_step
            is_unc = step.id == state.uncertain_step

            if is_done:
                icon_text = "[V]"
                color = self.COLOR_VERIFIED
            elif is_curr:
                icon_text = "[>]"
                color = self.COLOR_CURRENT
            elif is_unc:
                icon_text = "[?]"
                color = self.COLOR_UNCERTAIN
            else:
                icon_text = "[ ]"
                color = self.COLOR_PENDING

            step_line = f"{icon_text} {step.id}: {step.name[:18]}"
            cv2.putText(vis, step_line, (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            ty += 15

        ty += 4
        cv2.line(vis, (px + 8, ty - 6), (px + panel_w - 8, ty - 6), self.COLOR_BORDER, 1)

        # Current & Expected
        curr_id = state.current_step or "COMPLETE"
        cv2.putText(vis, f"CURRENT: {curr_id}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_CURRENT, 1, cv2.LINE_AA)
        ty += 16

        # Tri-State Assurance Decision Display
        if assurance_decision is not None:
            dec_val = assurance_decision.decision.value if hasattr(assurance_decision.decision, "value") else str(assurance_decision.decision)
            if dec_val == "VERIFIED":
                dec_color = (80, 230, 80)
            elif dec_val == "DEVIATION":
                dec_color = (50, 50, 245)  # Bright Red
            else:
                dec_color = (0, 165, 255)  # Orange

            dev_reason_str = ""
            if hasattr(assurance_decision, "deviation_reason") and assurance_decision.deviation_reason:
                r_val = assurance_decision.deviation_reason.value if hasattr(assurance_decision.deviation_reason, "value") else str(assurance_decision.deviation_reason)
                dev_reason_str = f" ({r_val})"

            cv2.putText(vis, f"DECISION: {dec_val}{dev_reason_str}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, dec_color, 1, cv2.LINE_AA)
            ty += 16
        else:
            status_color = self.COLOR_VERIFIED if state.procedure_status == ProcedureStatus.VERIFIED else (
                self.COLOR_UNCERTAIN if state.procedure_status == ProcedureStatus.UNCERTAIN else (200, 200, 200)
            )
            cv2.putText(vis, f"STATUS:  {state.procedure_status.value}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, status_color, 1)
            ty += 16

        # Recovery State Machine Status
        if recovery_state and recovery_state != "IDLE":
            rec_color = (60, 120, 255)
            cv2.putText(vis, f"RECOVERY: {recovery_state}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, rec_color, 1, cv2.LINE_AA)
            ty += 16

        # Evidence stats
        if bundle:
            verified_count = sum(1 for it in bundle.items.values() if it.verified)
            total_count = len(bundle.items)
            req_str = "PASS" if bundle.required_satisfied else "FAIL"
            cv2.putText(vis, f"EVIDENCE: {verified_count}/{total_count} ({req_str})", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 240, 140), 1)
            ty += 16

            conf_val = evaluation.confidence if evaluation else bundle.evidence_score
            cv2.putText(vis, f"CONFIDENCE: {conf_val:.2f}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
            ty += 16

        # Next Step
        next_id = state.next_expected_step or "NONE"
        cv2.putText(vis, f"NEXT:    {next_id}", (px + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 215, 255), 1)

        return vis
