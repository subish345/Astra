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
    """Toggles for rendering perception debug overlays and HUD telemetry."""
    show_boxes: bool = True
    show_tracks: bool = True
    show_pose: bool = True
    show_hands: bool = True
    show_confidence: bool = True
    show_fps: bool = True
    show_latency: bool = True
    show_system_state: bool = True
    show_hud: bool = True
    show_interactions: bool = True
    show_activity: bool = True
    detector_name: str = "ColorSpatialObjectDetector (Development Baseline)"


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

    def render(
        self,
        frame: np.ndarray,
        state: PerceptionState,
        mode: str = "PERCEPTION",
        target_name: str = "NONE",
        interaction_state: str = "NONE",
        activity_name: str = "IDLE",
        activity_confidence: float = 0.0,
    ) -> np.ndarray:
        """Render perception overlays, skeletons, hands, and telemetry HUD onto frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Render Tracks / Bounding Boxes
        if self.config.show_boxes or self.config.show_tracks:
            for track in state.tracks:
                if track.state == TrackState.LOST:
                    continue

                color = self.COLOR_MAP.get(track.class_name, self.COLOR_MAP["DEFAULT"])
                if track.state == TrackState.TEMPORARILY_LOST:
                    color = tuple(int(c * 0.5) for c in color)  # type: ignore

                bx1, by1 = int(track.bbox.x1), int(track.bbox.y1)
                bx2, by2 = int(track.bbox.x2), int(track.bbox.y2)

                cv2.rectangle(vis, (bx1, by1), (bx2, by2), color, 2)

                label_parts = []
                if self.config.show_tracks:
                    label_parts.append(f"#{track.track_id}")
                label_parts.append(track.class_name)
                if self.config.show_confidence:
                    label_parts.append(f"{track.confidence:.2f}")
                if track.state == TrackState.TEMPORARILY_LOST:
                    label_parts.append("[OCCLUDED]")

                label = " ".join(label_parts)
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(vis, (bx1, max(0, by1 - lh - 6)), (bx1 + lw + 6, max(lh + 6, by1)), color, -1)
                cv2.putText(vis, label, (bx1 + 3, max(lh, by1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

                # Trajectory trail
                if len(track.history) > 1:
                    pts = np.array(track.history, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(vis, [pts], isClosed=False, color=color, thickness=1)

        # 2. Render Pose Skeletons
        if self.config.show_pose:
            for pose in state.poses:
                kp_dict = {kp.name: (int(kp.x), int(kp.y)) for kp in pose.keypoints if kp.name}

                for pt1_name, pt2_name in self.POSE_CONNECTIONS:
                    if pt1_name in kp_dict and pt2_name in kp_dict:
                        p1 = kp_dict[pt1_name]
                        p2 = kp_dict[pt2_name]
                        cv2.line(vis, p1, p2, (0, 255, 255), 2, cv2.LINE_AA)

                for kp in pose.keypoints:
                    cv2.circle(vis, (int(kp.x), int(kp.y)), 4, (0, 165, 255), -1)

                if pose.bbox:
                    angle_text = f"TILT: {pose.orientation_angle:.2f} rad" if pose.orientation_angle is not None else ""
                    cv2.putText(vis, angle_text, (int(pose.bbox.x1), int(pose.bbox.y2 + 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        # 3. Render Hands
        if self.config.show_hands:
            for hand in state.hands:
                hx1, hy1 = int(hand.bbox.x1), int(hand.bbox.y1)
                hx2, hy2 = int(hand.bbox.x2), int(hand.bbox.y2)

                hand_color = (255, 120, 0) if hand.hand_type.value == "LEFT" else (0, 215, 255)
                cv2.rectangle(vis, (hx1, hy1), (hx2, hy2), hand_color, 1, cv2.LINE_AA)

                hand_label = f"{hand.hand_type.value} HAND ({hand.confidence:.2f})"
                cv2.putText(vis, hand_label, (hx1, max(15, hy1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, hand_color, 1)

                for kp in hand.keypoints:
                    cv2.circle(vis, (int(kp.x), int(kp.y)), 3, (255, 255, 255), -1)

        # 4. Translucent Aerospace Debug HUD
        if self.config.show_hud:
            overlay = vis.copy()
            hud_w = 265
            hud_h = 245
            hx, hy = 12, 12

            # Background box
            cv2.rectangle(overlay, (hx, hy), (hx + hud_w, hy + hud_h), (18, 20, 24), -1)
            cv2.rectangle(overlay, (hx, hy), (hx + hud_w, hy + hud_h), (70, 80, 95), 1)
            cv2.addWeighted(overlay, 0.78, vis, 0.22, 0, vis)

            # HUD Telemetry content
            ty = hy + 20
            # Header
            cv2.putText(vis, f"ASTRA-EA | {mode}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 255), 1, cv2.LINE_AA)
            ty += 20
            cv2.line(vis, (hx + 8, ty - 6), (hx + hud_w - 8, ty - 6), (60, 70, 80), 1)

            # Subsystem status
            cv2.putText(vis, "CAMERA:    ONLINE", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1)
            ty += 18
            cv2.putText(vis, "PERCEPTION:ONLINE", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1)
            ty += 18
            act_tracks = [t for t in state.tracks if t.is_active]
            cv2.putText(vis, f"TRACKING:  ONLINE ({len(act_tracks)} act)", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1)
            ty += 18

            # Detector info
            det_label = "ColorSpatialDev" if "ColorSpatial" in self.config.detector_name else "YOLOv8"
            cv2.putText(vis, f"DETECTOR:  {det_label}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (230, 200, 70), 1)
            ty += 18

            # Targets & Persons
            person_str = state.persons[0].person_id if state.persons else "STANDBY"
            cv2.putText(vis, f"PERSON:    {person_str}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)
            ty += 18

            hand_str = state.hands[0].hand_type.value if state.hands else "NONE"
            cv2.putText(vis, f"HAND:      {hand_str}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)
            ty += 18

            cv2.putText(vis, f"TARGET:    {target_name}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1)
            ty += 18

            cv2.putText(vis, f"INTERACT:  {interaction_state}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 215, 255), 1)
            ty += 18

            cv2.putText(vis, f"ACTIVITY:  {activity_name} ({activity_confidence:.2f})", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 255, 120), 1)
            ty += 20

            # FPS and Latency
            lat = state.latency
            fps_color = (0, 255, 128) if state.fps >= 20.0 else (0, 180, 255)
            cv2.putText(vis, f"FPS: {state.fps:.1f}  LAT: {lat.total_ms:.1f}ms", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.40, fps_color, 1, cv2.LINE_AA)

        # 5. Interactive Keyboard Controls Bar (Bottom)
        bot_y = h - 8
        bar_text = "[P]ose [H]ands [O]bjects [T]racks [I]nt [A]ct [D]ebug [E]vidence [R]eset [Q]uit"
        cv2.putText(vis, bar_text, (10, bot_y), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (160, 175, 190), 1, cv2.LINE_AA)

        return vis
