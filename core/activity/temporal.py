"""Rolling temporal observation buffer and kinematic feature extraction for activities.

Maintains a bounded sliding time window and derives velocity, acceleration,
displacement, contact duration, and relative motion profiles.
"""

from __future__ import annotations

import collections
import math
from typing import Deque, Dict, List, Optional, Tuple

from core.activity.types import TemporalFeatureSet, TemporalWindow
from core.interaction.types import InteractionEvent, InteractionState


class TemporalBuffer:
    """Sliding circular buffer storing timestamped interaction and track events."""

    def __init__(self, window_seconds: float = 5.0, max_capacity: int = 300):
        self.window_seconds = window_seconds
        self.max_capacity = max_capacity
        # Deque of tuples: (timestamp, List[InteractionEvent], Dict[track_id, (center_x, center_y)])
        self._buffer: Deque[Tuple[float, List[InteractionEvent], Dict[int, Tuple[float, float]]]] = collections.deque(
            maxlen=max_capacity
        )

    def append(
        self,
        timestamp: float,
        interactions: List[InteractionEvent],
        track_positions: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> None:
        """Add new observations and prune expired entries outside the time window."""
        positions = dict(track_positions or {})
        self._buffer.append((timestamp, list(interactions), positions))
        self._prune_expired(timestamp)

    def _prune_expired(self, current_timestamp: float) -> None:
        """Evict records older than window_seconds from the buffer head."""
        cutoff = current_timestamp - self.window_seconds
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

    def get_slice(self, start_time: float, end_time: float) -> List[Tuple[float, List[InteractionEvent], Dict[int, Tuple[float, float]]]]:
        """Retrieve observations within the requested time bounds [start_time, end_time]."""
        return [item for item in self._buffer if start_time <= item[0] <= end_time]

    def get_interaction_history(
        self,
        hand_type: str,
        track_id: int,
        duration: Optional[float] = None,
    ) -> List[InteractionEvent]:
        """Retrieve temporal sequence of InteractionEvents for a specific hand-object pair."""
        if not self._buffer:
            return []

        latest_time = self._buffer[-1][0]
        cutoff = latest_time - (duration or self.window_seconds)

        history: List[InteractionEvent] = []
        for ts, events, _ in self._buffer:
            if ts >= cutoff:
                for ev in events:
                    ht = ev.hand_type.value if hasattr(ev.hand_type, "value") else str(ev.hand_type)
                    if ht == hand_type and ev.target_track_id == track_id:
                        history.append(ev)
        return history

    def get_track_trajectory(
        self,
        track_id: int,
        duration: Optional[float] = None,
    ) -> List[Tuple[float, Tuple[float, float]]]:
        """Retrieve timestamped (x, y) coordinates for a specific track."""
        if not self._buffer:
            return []

        latest_time = self._buffer[-1][0]
        cutoff = latest_time - (duration or self.window_seconds)

        trajectory: List[Tuple[float, Tuple[float, float]]] = []
        for ts, _, pos_dict in self._buffer:
            if ts >= cutoff and track_id in pos_dict:
                trajectory.append((ts, pos_dict[track_id]))
        return trajectory

    def to_temporal_window(self) -> TemporalWindow:
        """Export current buffer as a TemporalWindow."""
        if not self._buffer:
            return TemporalWindow(0.0, 0.0, [])
        start_ts = self._buffer[0][0]
        end_ts = self._buffer[-1][0]
        all_events = [ev for _, evs, _ in self._buffer for ev in evs]
        return TemporalWindow(start_time=start_ts, end_time=end_ts, interactions=all_events)

    def clear(self) -> None:
        """Flush the buffer."""
        self._buffer.clear()


class TemporalFeatureExtractor:
    """Extracts kinematic and temporal features over observation trajectories."""

    @classmethod
    def extract_features(
        cls,
        interaction_history: List[InteractionEvent],
        trajectory: List[Tuple[float, Tuple[float, float]]],
    ) -> TemporalFeatureSet:
        """Compute kinematic metrics across interaction history and spatial trajectory."""
        if not interaction_history and not trajectory:
            return TemporalFeatureSet()

        # 1. Temporal bounds
        t_start = trajectory[0][0] if trajectory else interaction_history[0].timestamp
        t_end = trajectory[-1][0] if trajectory else interaction_history[-1].timestamp
        duration = max(0.001, t_end - t_start)

        # 2. Object displacement & velocity
        if len(trajectory) >= 2:
            p_start = trajectory[0][1]
            p_end = trajectory[-1][1]
            dx = round(p_end[0] - p_start[0], 2)
            dy = round(p_end[1] - p_start[1], 2)
            displacement = round(math.hypot(dx, dy), 2)
            vx = round(dx / duration, 2)
            vy = round(dy / duration, 2)

            # Acceleration: compare velocity in first half vs second half
            mid_idx = len(trajectory) // 2
            p_mid = trajectory[mid_idx][1]
            t_mid = trajectory[mid_idx][0]
            dt1 = max(0.001, t_mid - t_start)
            dt2 = max(0.001, t_end - t_mid)
            v1 = ((p_mid[0] - p_start[0]) / dt1, (p_mid[1] - p_start[1]) / dt1)
            v2 = ((p_end[0] - p_mid[0]) / dt2, (p_end[1] - p_mid[1]) / dt2)
            ax = round((v2[0] - v1[0]) / duration, 2)
            ay = round((v2[1] - v1[1]) / duration, 2)
        else:
            dx, dy, displacement = 0.0, 0.0, 0.0
            vx, vy = 0.0, 0.0
            ax, ay = 0.0, 0.0

        # 3. Distance change & contact duration
        contact_states = {
            InteractionState.CONTACT,
            InteractionState.GRASPING,
            InteractionState.HOLDING,
            InteractionState.MOVING,
        }
        contact_duration = 0.0
        dist_change = 0.0
        correlations: List[float] = []

        if interaction_history:
            d_start = interaction_history[0].distance
            d_end = interaction_history[-1].distance
            dist_change = round(d_end - d_start, 4)

            for i in range(len(interaction_history)):
                ev = interaction_history[i]
                if ev.state in contact_states:
                    dt_sample = (
                        interaction_history[i].timestamp - interaction_history[i - 1].timestamp
                        if i > 0
                        else 0.033
                    )
                    contact_duration += max(0.0, dt_sample)

                if ev.spatial and ev.spatial.motion_correlation != 0.0:
                    correlations.append(ev.spatial.motion_correlation)

        mean_motion_corr = round(sum(correlations) / len(correlations), 2) if correlations else 0.0

        return TemporalFeatureSet(
            position_delta=(dx, dy),
            velocity=(vx, vy),
            acceleration=(ax, ay),
            distance_change=dist_change,
            contact_duration=round(contact_duration, 3),
            object_displacement=displacement,
            hand_object_relative_motion=mean_motion_corr,
            vertical_displacement=dy,
            duration_seconds=round(duration, 3),
        )
