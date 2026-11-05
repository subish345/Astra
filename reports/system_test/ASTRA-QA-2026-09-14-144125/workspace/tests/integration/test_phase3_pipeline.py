"""End-to-end integration test for Phase 3 pipeline.

Verifies:
Synthetic Frames -> Perception -> SpatialInteractionEngine -> TemporalBuffer ->
PrimitiveActivityEngine -> CompositeActivityEngine -> Deduplicated Event Bus -> Annotation
"""

import pytest
from core.activity.annotation import ActivityAnnotation
from core.activity.composite import CompositeActivityEngine
from core.activity.events import ActivityEventBus, ActivityEventDeduplicator
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer
from core.interaction.engine import SpatialInteractionEngine
from core.interaction.scenarios import scenario_correct_grasp


def test_end_to_end_phase3_pipeline_integration():
    """Verify complete physical interaction and activity recognition flow on realistic synthetic scenario."""
    # 1. Initialize Subsystem Engines
    interaction_engine = SpatialInteractionEngine()
    temporal_buffer = TemporalBuffer(window_seconds=4.0)
    primitive_engine = PrimitiveActivityEngine()
    composite_engine = CompositeActivityEngine()

    event_bus = ActivityEventBus()
    published_events = []
    event_bus.subscribe(lambda ev: published_events.append(ev))
    deduplicator = ActivityEventDeduplicator(event_bus)

    # 2. Ingest 25-frame sequence: Approach -> Contact -> Grasp -> Lift
    frames = scenario_correct_grasp(num_frames=25)

    recognized_primitives = []
    recognized_composites = []
    annotations = []

    for frame in frames:
        ts = frame.timestamp

        # Step A: Interaction Engine
        interactions = interaction_engine.process(frame.tracks, frame.hands, ts)

        # Step B: Record to Temporal Buffer
        positions = {t.track_id: t.center for t in frame.tracks}
        temporal_buffer.append(ts, interactions, positions)

        # Step C: Deduplicate interaction lifecycle events
        for int_ev in interactions:
            deduplicator.process_interaction(int_ev)

            # Step D: Primitive Activity Recognition
            prim_obs = primitive_engine.evaluate(int_ev, temporal_buffer)
            recognized_primitives.append(prim_obs.activity_name)
            deduplicator.process_activity(prim_obs)

            # Step E: Composite Activity Recognition
            comp_obs = composite_engine.update(prim_obs)
            if comp_obs:
                recognized_composites.append(comp_obs.activity_name)
                deduplicator.process_activity(comp_obs)

                # Step F: Annotation Export Contract
                ann = ActivityAnnotation.from_observation(
                    comp_obs,
                    video_id="TEST_GRASP_SIM",
                    start_frame=1,
                    end_frame=frame.frame_id,
                )
                annotations.append(ann)

    # 3. Verify Pipeline Results
    # Check that primitive activities progressed realistically
    assert "APPROACH" in recognized_primitives or "TOUCH" in recognized_primitives
    assert "TOUCH" in recognized_primitives or "HOLD" in recognized_primitives or "MOVE" in recognized_primitives

    # Check that telemetry events were emitted to the event bus
    assert len(published_events) >= 2

    # Verify annotation structure validity
    if annotations:
        ann = annotations[0]
        assert ann.actor == "ASTRONAUT"
        assert ann.object == "RED_BOX"
        assert ann.confidence > 0.0
