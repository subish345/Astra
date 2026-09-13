"""Perception debug visualization overlay renderer for ASTRA-EA.

Renders high-contrast bounding boxes, persistent tracking IDs, pose skeletons,
hand landmarks, FPS counters, and latency telemetry directly onto OpenCV frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import cv2
import numpy as np

from core.perception.types import PerceptionState, TrackState


@dataclass
class OverlayConfig:
    """Toggles for rendering perception debug overlays."""
    show_boxes: bool = True
    show_tracks: bool = True
    show_pose: bool = True
    show_hands: bool = True
    show_confidence: bool = True
    show_fps: bool = True
    show_latency: bool = True
    show_system_state: bool = True


class PerceptionVisualizer:
    """Renders space-operations visual telemetry overlays on video frames."""

    # Color palette for classes (BGR)
    COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
        "RED_BOX": (40, 40, 230),       # High-visibility Red
        "YELLOW_BOX": (30, 215, 230),   # High-visibility Yellow
        "MAIN_BOX": (225, 140, 30),     # Cyan / Blue
        "ASTRONAUT": (50, 220, 50),     # Bright Green
        "DEFAULT": (200, 200, 200),
    }

    POSE_CONNECTIONS = [
        ("nose", "left_shoulder"),
        ("nose", "right_shoulder"),
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
    ]

    def __init__(self, config: OverlayConfig = None):
        self.config = config or OverlayConfig()

    def render(self, frame: np.ndarray, state: PerceptionState) -> np.ndarray:
        """Render perception overlays onto a copy of the input frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Render Tracks / Bounding Boxes
        if self.config.show_boxes or self.config.show_tracks:
            for track in state.tracks:
                if track.state == TrackState.LOST:
                    continue

                color = self.COLOR_MAP.get(track.class_name, self.COLOR_MAP["DEFAULT"])
                # Dim color if temporarily lost
                if track.state == TrackState.TEMPORARILY_LOST:
                    color = tuple(int(c * 0.5) for c in color)  # type: ignore

                bx1, by1 = int(track.bbox.x1), int(track.bbox.y1)
                bx2, by2 = int(track.bbox.x2), int(track.bbox.y2)

                # Draw corner brackets or rectangle
                cv2.rectangle(vis, (bx1, by1), (bx2, by2), color, 2)

                # Label tag
                label_parts = []
                if self.config.show_tracks:
                    label_parts.append(f"#{track.track_id}")
                label_parts.append(track.class_name)
                if self.config.show_confidence:
                    label_parts.append(f"{track.confidence:.2f}")
                if track.state == TrackState.TEMPORARILY_LOST:
                    label_parts.append("[OCCLUDED]")

                label = " ".join(label_parts)
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(vis, (bx1, max(0, by1 - lh - 6)), (bx1 + lw + 6, max(lh + 6, by1)), color, -1)
                cv2.putText(vis, label, (bx1 + 3, max(lh, by1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

                # Trajectory trail
                if len(track.history) > 1:
                    pts = np.array(track.history, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(vis, [pts], isClosed=False, color=color, thickness=1)

        # 2. Render Pose Skeletons
        if self.config.show_pose:
            for pose in state.poses:
                kp_dict = {kp.name: (int(kp.x), int(kp.y)) for kp in pose.keypoints if kp.name}

                # Draw bones
                for pt1_name, pt2_name in self.POSE_CONNECTIONS:
                    if pt1_name in kp_dict and pt2_name in kp_dict:
                        p1 = kp_dict[pt1_name]
                        p2 = kp_dict[pt2_name]
                        cv2.line(vis, p1, p2, (0, 255, 255), 2, cv2.LINE_AA)

                # Draw landmark joints
                for kp in pose.keypoints:
                    cv2.circle(vis, (int(kp.x), int(kp.y)), 4, (0, 165, 255), -1)

                # Orientation angle banner
                if pose.bbox:
                    angle_text = f"TILT: {pose.orientation_angle:.2f} rad" if pose.orientation_angle is not None else ""
                    cv2.putText(vis, angle_text, (int(pose.bbox.x1), int(pose.bbox.y2 + 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        # 3. Render Hands
        if self.config.show_hands:
            for hand in state.hands:
                hx1, hy1 = int(hand.bbox.x1), int(hand.bbox.y1)
                hx2, hy2 = int(hand.bbox.x2), int(hand.bbox.y2)

                hand_color = (255, 100, 0) if hand.hand_type.value == "LEFT" else (0, 200, 255)
                cv2.rectangle(vis, (hx1, hy1), (hx2, hy2), hand_color, 1, cv2.LINE_AA)

                hand_label = f"{hand.hand_type.value} HAND ({hand.confidence:.2f})"
                cv2.putText(vis, hand_label, (hx1, max(15, hy1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, hand_color, 1)

                for kp in hand.keypoints:
                    cv2.circle(vis, (int(kp.x), int(kp.y)), 3, (255, 255, 255), -1)

        # 4. Telemetry Header Banner
        header_y = 25
        if self.config.show_fps:
            fps_text = f"FPS: {state.fps:.1f}"
            cv2.putText(vis, fps_text, (15, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
            header_y += 25

        if self.config.show_latency:
            lat = state.latency
            lat_text = f"LATENCY: {lat.total_ms:.1f}ms (det:{lat.detection_ms:.0f} trk:{lat.tracking_ms:.0f} pose:{lat.pose_ms:.0f} hand:{lat.hand_ms:.0f})"
            cv2.putText(vis, lat_text, (15, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1, cv2.LINE_AA)
            header_y += 22

        if self.config.show_system_state:
            sys_text = f"FRAME: #{state.frame_id} | DEV: ONLINE | AI: ACTIVE"
            cv2.putText(vis, sys_text, (15, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        return vis
