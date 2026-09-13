"""Spatial-temporal multi-object tracker with occlusion handling for ASTRA-EA.

Maintains persistent track IDs, computes centroid velocities, and implements
an occlusion lifecycle (VISIBLE -> TEMPORARILY_LOST -> REACQUIRED -> LOST)
to ensure stable identity tracking across transient hand/object occlusions.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from core.perception.tracking.interface import Tracker
from core.perception.types import BoundingBox, Detection, Track, TrackState


class MultiObjectTracker(Tracker):
    """Associates detections using IoU and spatial proximity with occlusion grace periods."""

    def __init__(
        self,
        iou_threshold: float = 0.25,
        max_lost_frames: int = 20,  # ~0.67s at 30 FPS
        history_len: int = 30,
    ):
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.history_len = history_len

        self._next_id = 1
        self._tracks: Dict[int, Track] = {}

    def update(self, detections: List[Detection], frame_id: int) -> List[Track]:
        """Update existing tracks and register new detections."""
        active_track_ids = list(self._tracks.keys())
        matched_detections = set()
        matched_tracks = set()

        # 1. Compute IoU cost matrix between active tracks and detections
        for track_id in active_track_ids:
            track = self._tracks[track_id]
            best_iou = 0.0
            best_det_idx = -1

            for det_idx, det in enumerate(detections):
                if det_idx in matched_detections:
                    continue
                # Class name must match for identity continuity
                if det.class_name != track.class_name:
                    continue

                iou = track.bbox.iou(det.bbox)
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_det_idx = det_idx

            if best_det_idx >= 0:
                det = detections[best_det_idx]
                matched_detections.add(best_det_idx)
                matched_tracks.add(track_id)

                # Calculate velocity
                prev_cx, prev_cy = track.center
                new_cx, new_cy = det.center
                vx = round(new_cx - prev_cx, 2)
                vy = round(new_cy - prev_cy, 2)

                # Determine state transition
                new_state = TrackState.REACQUIRED if track.lost_frames > 0 else TrackState.VISIBLE

                # Update track
                track.bbox = det.bbox
                track.confidence = det.confidence
                track.velocity = (vx, vy)
                track.history.append((new_cx, new_cy))
                if len(track.history) > self.history_len:
                    track.history.pop(0)
                track.age_frames += 1
                track.lost_frames = 0
                track.state = new_state
                track.is_active = True

                # Assign track ID back to detection
                det.track_id = track.track_id

        # 2. Handle unmatched tracks (occluded or disappeared)
        unmatched_track_ids = set(active_track_ids) - matched_tracks
        for track_id in unmatched_track_ids:
            track = self._tracks[track_id]
            track.lost_frames += 1
            if track.lost_frames > self.max_lost_frames:
                track.state = TrackState.LOST
                track.is_active = False
            else:
                track.state = TrackState.TEMPORARILY_LOST

        # 3. Create new tracks for unmatched detections
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_detections:
                new_track = Track(
                    track_id=self._next_id,
                    class_name=det.class_name,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    velocity=(0.0, 0.0),
                    history=[det.center],
                    age_frames=1,
                    lost_frames=0,
                    state=TrackState.VISIBLE,
                    is_active=True,
                )
                det.track_id = self._next_id
                self._tracks[self._next_id] = new_track
                self._next_id += 1

        # Clean up tracks that exceeded lost threshold
        dead_tracks = [tid for tid, t in self._tracks.items() if not t.is_active]
        for tid in dead_tracks:
            del self._tracks[tid]

        # Return list of active tracks (including temporarily lost for continuity)
        return list(self._tracks.values())

    def reset(self) -> None:
        """Reset tracking state and identity counters."""
        self._next_id = 1
        self._tracks.clear()

    @property
    def tracker_name(self) -> str:
        return "MultiObjectTracker"
