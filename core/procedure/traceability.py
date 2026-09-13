"""Step Traceability (D4.07) for ASTRA-EA.

Constructs detailed, inspectable causal audit chains linking step verification
decisions back through evidence factors, activities, interactions, tracked bounding boxes,
and exact video timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.activity.types import ActivityObservation
from core.evidence.types import EvidenceBundle
from core.interaction.types import InteractionEvent
from core.procedure.types import StepCandidate, StepEvaluation


@dataclass
class StepTraceRecord:
    """Full causal audit lineage for a procedural verification decision."""
    evaluation: StepEvaluation
    candidate: Optional[StepCandidate] = None
    bundle: Optional[EvidenceBundle] = None
    activity: Optional[ActivityObservation] = None
    interactions: List[InteractionEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format_tree(self) -> str:
        """Render a clean ASCII tree showing the causal lineage answering 'Why was this verified/uncertain?'"""
        status_symbol = "✓" if self.evaluation.status.value == "VERIFIED" else ("?" if self.evaluation.status.value == "UNCERTAIN" else "✗")
        lines = [
            f"STEP AUDIT TRACE: [{self.evaluation.step_id}] — {status_symbol} {self.evaluation.status.value}",
            f"├── Experiment: {self.evaluation.experiment_id} (Procedure v{self.evaluation.procedure_version})",
            f"├── Run / Eval: {self.evaluation.run_id} / {self.evaluation.evaluation_id}",
            f"├── Software / Model: v{self.evaluation.software_version} / {self.evaluation.model_version}",
            f"├── Confidence: {self.evaluation.confidence:.2%}",
        ]

        exp_seq = self.evaluation.metadata.get("expected_action_sequence")
        obs_actions = self.evaluation.metadata.get("observed_actions", [])
        if exp_seq:
            seq_str = " → ".join(exp_seq)
            lines.append(f"├── Action Sequence:")
            lines.append(f"│   ├── Expected: {seq_str}")
            obs_parts = []
            for act in exp_seq:
                check = "✓" if act in obs_actions else "✗"
                obs_parts.append(f"{act} {check}")
            lines.append(f"│   └── Sub-Actions: {', '.join(obs_parts)}")

        if self.candidate:
            lines.append(f"├── Candidate Match:")
            lines.append(f"│   ├── Action: {self.candidate.activity_type} (score: {self.candidate.match_score:.2f})")
            lines.append(f"│   ├── Target Object: {self.candidate.object_id or 'NONE'}")
            lines.append(f"│   └── Actor: {self.candidate.actor}")

        if self.activity:
            lines.append(f"├── Activity Observation:")
            lines.append(f"│   ├── Concept: {self.activity.activity_name} (conf: {self.activity.confidence:.2f})")
            lines.append(f"│   ├── Time Window: [{self.activity.start_time:.2f}s -> {self.activity.end_time:.2f}s] ({self.activity.duration_seconds:.2f}s)")
            if self.activity.target_track_id is not None:
                lines.append(f"│   └── Track ID: #{self.activity.target_track_id}")

        if self.bundle:
            lines.append(f"├── Evidence Corroboration (Bundle: {self.bundle.bundle_id}):")
            lines.append(f"│   ├── Score: {self.bundle.evidence_score:.2f} | Required Satisfied: {self.bundle.required_satisfied}")
            if self.bundle.missing_required:
                lines.append(f"│   ├── Missing Required: {self.bundle.missing_required}")
            if self.bundle.source_frames:
                frame_span = f"{min(self.bundle.source_frames)}–{max(self.bundle.source_frames)}" if len(self.bundle.source_frames) > 1 else str(self.bundle.source_frames[0])
                lines.append(f"│   ├── Source Frames: [{frame_span}]")
            for k, item in self.bundle.items.items():
                mark = "✓" if item.verified else "✗"
                lines.append(f"│   ├── {mark} {item.evidence_type.value}: conf={item.confidence:.2f}")

        lines.append(f"└── Decision Reasons:")
        for r in self.evaluation.reasons:
            lines.append(f"    • {r}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full trace record to structured dictionary for audit persistence."""
        return {
            "evaluation": self.evaluation.to_dict(),
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "bundle": self.bundle.to_dict() if self.bundle else None,
            "activity_id": self.activity.activity_id if self.activity else None,
            "reasons": self.evaluation.reasons,
            "metadata": self.metadata,
        }
