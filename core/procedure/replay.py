"""Procedure Replay Engine (D4.11) for ASTRA-EA.

Replays recorded activity/event sequences deterministically through the procedure engine,
reconstructing current steps, verification decisions, uncertainty, and next expected steps
without requiring live video or sensor hardware.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.activity.types import ActivityObservation, ActivityStatus, TemporalWindow
from core.evidence.engine import MultimodalEvidenceEngine
from core.evidence.types import EvidenceBundle
from core.procedure.progress import ProcedureProgressManager
from core.procedure.schema import ExperimentDefinition
from core.procedure.types import ProcedureState, StepEvaluation


class ProcedureReplayer:
    """Executes offline deterministic procedure evaluation against recorded event logs."""

    def __init__(
        self,
        procedure: ExperimentDefinition,
        run_id: str = "REPLAY_001",
        evidence_engine: Optional[MultimodalEvidenceEngine] = None,
        database_manager: Optional[Any] = None,
    ):
        self.procedure = procedure
        self.run_id = run_id
        self.evidence_engine = evidence_engine or MultimodalEvidenceEngine()
        self.database_manager = database_manager
        self.manager = ProcedureProgressManager(procedure=procedure, run_id=run_id)

    def replay_from_file(self, event_file_path: str | Path) -> Dict[str, Any]:
        """Load an event sequence from a JSON file and replay it."""
        path = Path(event_file_path)
        if not path.exists():
            raise FileNotFoundError(f"Event replay file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data if isinstance(data, list) else data.get("events", data.get("activities", []))
        return self.replay_sequence(events)

    def replay_sequence(self, event_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replay a list of activity/event dictionaries through the procedure progress engine."""
        self.manager.reset()
        history: List[Dict[str, Any]] = []

        step_map = {s.id: s for s in self.procedure.steps}

        for idx, rec in enumerate(event_records):
            act_name = rec.get("activity_name", rec.get("activity", "IDLE"))
            actor = rec.get("actor", "ASTRONAUT")
            target_obj = rec.get("target_object_id", rec.get("object", None))
            conf = float(rec.get("confidence", 0.90))
            t_start = float(rec.get("start_time", rec.get("timestamp_start", idx * 1.0)))
            t_end = float(rec.get("end_time", rec.get("timestamp_end", t_start + 1.0)))
            act_id = rec.get("activity_id", f"ACT_REP_{idx:04d}")

            obs = ActivityObservation(
                activity_name=act_name,
                actor=actor,
                target_object_id=target_obj,
                confidence=conf,
                window=TemporalWindow(start_time=t_start, end_time=t_end),
                activity_id=act_id,
                status=ActivityStatus.CONFIRMED,
            )

            # Check if an explicit evidence bundle dictionary was provided in the recording
            bundle = None
            if "evidence" in rec and isinstance(rec["evidence"], dict):
                ev_data = rec["evidence"]
                bundle = EvidenceBundle(
                    activity_id=act_id,
                    activity_name=act_name,
                    target_object_id=target_obj,
                    timestamp=t_end,
                    evidence_score=float(ev_data.get("score", conf)),
                    required_satisfied=bool(ev_data.get("required_satisfied", True)),
                    timestamp_range=(t_start, t_end),
                )
            else:
                # Use MultimodalEvidenceEngine against candidate step
                curr_step_id = self.manager.current_step
                step_def = step_map.get(curr_step_id) if curr_step_id else None
                bundle = self.evidence_engine.evaluate(
                    activity=obs,
                    step=step_def,
                )

            # Process through progress manager
            state = self.manager.update(activity=obs, bundle=bundle, timestamp=t_end)

            if self.database_manager:
                if self.manager.last_evaluation:
                    self.database_manager.record_step_evaluation(self.manager.last_evaluation)
                if bundle:
                    self.database_manager.record_evidence_bundle(bundle)
                self.database_manager.record_procedure_progress(state)

            history.append({
                "event_index": idx,
                "activity": obs.activity_name,
                "target_object": obs.target_object_id,
                "timestamp": t_end,
                "state": state.to_dict(),
            })

        final_state = self.manager.get_state()
        return {
            "experiment_id": self.procedure.experiment.id,
            "run_id": self.run_id,
            "total_events_processed": len(event_records),
            "completed_steps": list(final_state.completed_steps),
            "final_current_step": final_state.current_step,
            "final_next_expected": final_state.next_expected_step,
            "final_status": final_state.procedure_status.value,
            "history": history,
        }
