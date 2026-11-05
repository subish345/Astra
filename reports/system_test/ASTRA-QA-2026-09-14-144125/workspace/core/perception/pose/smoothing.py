"""Adaptive temporal pose smoothing for ASTRA-EA.

Applies velocity-adaptive exponential smoothing (One-Euro filter principles) to 33-point
skeletal landmarks, removing high-frequency sensor noise and jitter while maintaining
instantaneous responsiveness during fast astronaut manipulation and translation.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.perception.types import Keypoint, PoseObservation


class TemporalPoseSmoother:
    """Velocity-adaptive exponential smoothing filter for skeletal landmarks."""

    def __init__(
        self,
        min_cutoff: float = 0.05,
        beta: float = 0.8,
        derivate_cutoff: float = 1.0,
        max_missing_seconds: float = 0.5,
    ):
        """
        Args:
            min_cutoff: Minimum filter coefficient (low-speed smoothing).
            beta: Speed coefficient adjusting cutoff frequency proportional to velocity.
            derivate_cutoff: Cutoff for velocity derivation.
            max_missing_seconds: Time before stale filter state is purged.
        """
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.derivate_cutoff = derivate_cutoff
        self.max_missing_seconds = max_missing_seconds

        # Key: (person_id, landmark_name) -> (prev_time, smoothed_pos_xyz, smoothed_vel_xyz)
        self._states: Dict[Tuple[int, str], Tuple[float, np.ndarray, np.ndarray]] = {}

    def smooth(self, poses: List[PoseObservation], timestamp: Optional[float] = None) -> List[PoseObservation]:
        """Smooth all keypoints in the given pose observations."""
        now = timestamp if timestamp is not None else time.time()
        smoothed_poses: List[PoseObservation] = []

        # Purge stale landmark tracks
        stale_keys = [
            k for k, (t_prev, _, _) in self._states.items()
            if (now - t_prev) > self.max_missing_seconds
        ]
        for k in stale_keys:
            del self._states[k]

        for pose in poses:
            smoothed_keypoints: List[Keypoint] = []
            for kp in pose.keypoints:
                if not kp.name:
                    smoothed_keypoints.append(kp)
                    continue

                key = (pose.person_id, kp.name.lower())
                curr_pos = np.array([kp.x, kp.y, kp.z if kp.z is not None else 0.0], dtype=np.float64)

                if key not in self._states:
                    # First observation for this keypoint
                    self._states[key] = (now, curr_pos, np.zeros(3, dtype=np.float64))
                    smoothed_keypoints.append(kp)
                else:
                    prev_time, prev_pos, prev_vel = self._states[key]
                    dt = max(now - prev_time, 1e-4)

                    # Compute instantaneous velocity
                    raw_vel = (curr_pos - prev_pos) / dt
                    alpha_v = self._calc_alpha(self.derivate_cutoff, dt)
                    filtered_vel = alpha_v * raw_vel + (1.0 - alpha_v) * prev_vel

                    # Compute adaptive cutoff based on velocity magnitude
                    speed = float(np.linalg.norm(filtered_vel[:2]))  # 2D screen speed
                    cutoff = self.min_cutoff + self.beta * speed
                    alpha = self._calc_alpha(cutoff, dt)

                    # Smooth position
                    filtered_pos = alpha * curr_pos + (1.0 - alpha) * prev_pos

                    self._states[key] = (now, filtered_pos, filtered_vel)

                    smoothed_keypoints.append(
                        Keypoint(
                            x=float(filtered_pos[0]),
                            y=float(filtered_pos[1]),
                            z=float(filtered_pos[2]) if kp.z is not None else None,
                            confidence=kp.confidence,
                            name=kp.name,
                        )
                    )

            smoothed_poses.append(
                PoseObservation(
                    person_id=pose.person_id,
                    keypoints=smoothed_keypoints,
                    confidence=pose.confidence,
                    bbox=pose.bbox,
                    orientation_angle=pose.orientation_angle,
                    source=pose.source,
                )
            )

        return smoothed_poses

    def reset(self) -> None:
        """Reset internal filter states."""
        self._states.clear()

    @staticmethod
    def _calc_alpha(cutoff: float, dt: float) -> float:
        """Calculate smoothing factor alpha based on cutoff frequency and time step."""
        tau = 1.0 / (2.0 * np.pi * max(cutoff, 1e-4))
        alpha = 1.0 / (1.0 + tau / max(dt, 1e-4))
        return float(np.clip(alpha, 0.05, 1.0))
