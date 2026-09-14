"""Perception debug visualization overlay renderer for ASTRA-EA.

Renders cyber-aerospace visual telemetry: 33-point glowing skeletal wireframes,
concentric hand reticles, laser targeting beams, alpha-decay trajectory trails,
and HUD telemetry directly onto OpenCV frames.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple
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
    show_laser_guides: bool = True
    detector_name: str = "ColorSpatialObjectDetector (Development Baseline)"


class PerceptionVisualizer:
    """Renders space-operations visual telemetry overlays on video frames."""

    # Color palette for classes (BGR)
    COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
        "RED_BOX": (40, 40, 230),       # High-visibility Red
        "YELLOW_BOX": (30, 215, 230),   # High-visibility Yellow
        "MAIN_BOX": (225, 140, 30),     # Cyan / Blue
        "WORK_SURFACE": (180, 180, 180),# Neutral Gray
        "ASTRONAUT": (50, 220, 50),     # Bright Green
        "DEFAULT": (200, 200, 200),
    }

    # 33-Keypoint BlazePose Color-Coded Skeletal Bones: (pt1, pt2, BGR_color, thickness)
    BLAZEPOSE_BONES: List[Tuple[str, str, Tuple[int, int, int], int]] = [
        # Torso & Ribcage Box (Emerald Green)
        ("left_shoulder", "right_shoulder", (0, 230, 118), 3),
        ("left_shoulder", "left_hip", (0, 230, 118), 3),
        ("right_shoulder", "right_hip", (0, 230, 118), 3),
        ("left_hip", "right_hip", (0, 230, 118), 3),
        # Left Arm (Electric Magenta)
        ("left_shoulder", "left_elbow", (214, 112, 218), 3),
        ("left_elbow", "left_wrist", (214, 112, 218), 3),
        # Right Arm (Neon Amber)
        ("right_shoulder", "right_elbow", (0, 165, 255), 3),
        ("right_elbow", "right_wrist", (0, 165, 255), 3),
        # Left Hand Web
        ("left_wrist", "left_pinky", (214, 112, 218), 2),
        ("left_wrist", "left_index", (214, 112, 218), 2),
        ("left_wrist", "left_thumb", (214, 112, 218), 2),
        ("left_pinky", "left_index", (214, 112, 218), 1),
        # Right Hand Web
        ("right_wrist", "right_pinky", (0, 165, 255), 2),
        ("right_wrist", "right_index", (0, 165, 255), 2),
        ("right_wrist", "right_thumb", (0, 165, 255), 2),
        ("right_pinky", "right_index", (0, 165, 255), 1),
        # Face & Head (Cyan)
        ("nose", "left_eye", (0, 229, 255), 2),
        ("left_eye", "left_ear", (0, 229, 255), 2),
        ("nose", "right_eye", (0, 229, 255), 2),
        ("right_eye", "right_ear", (0, 229, 255), 2),
        # Lower Body Legs & Foot Restraints (Emerald Green)
        ("left_hip", "left_knee", (0, 230, 118), 3),
        ("left_knee", "left_ankle", (0, 230, 118), 3),
        ("left_ankle", "left_heel", (0, 230, 118), 2),
        ("left_ankle", "left_foot_index", (0, 230, 118), 2),
        ("left_heel", "left_foot_index", (0, 230, 118), 2),
        ("right_hip", "right_knee", (0, 230, 118), 3),
        ("right_knee", "right_ankle", (0, 230, 118), 3),
        ("right_ankle", "right_heel", (0, 230, 118), 2),
        ("right_ankle", "right_foot_index", (0, 230, 118), 2),
        ("right_heel", "right_foot_index", (0, 230, 118), 2),
    ]

    # Legacy 9-point fallback connections
    LEGACY_POSE_CONNECTIONS: List[Tuple[str, str, Tuple[int, int, int], int]] = [
        ("nose", "left_shoulder", (0, 229, 255), 2),
        ("nose", "right_shoulder", (0, 229, 255), 2),
        ("left_shoulder", "right_shoulder", (0, 230, 118), 3),
        ("left_shoulder", "left_elbow", (214, 112, 218), 3),
        ("left_elbow", "left_wrist", (214, 112, 218), 3),
        ("right_shoulder", "right_elbow", (0, 165, 255), 3),
        ("right_elbow", "right_wrist", (0, 165, 255), 3),
        ("left_shoulder", "left_hip", (0, 230, 118), 2),
        ("right_shoulder", "right_hip", (0, 230, 118), 2),
        ("left_hip", "right_hip", (0, 230, 118), 2),
    ]

    def __init__(self, config: Optional[OverlayConfig] = None):
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
        """Render cyber-aerospace overlays, skeletons, hands, and telemetry HUD onto frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Render Tracks / Bounding Boxes & Glowing Trajectory Trails
        if self.config.show_boxes or self.config.show_tracks:
            for track in state.tracks:
                if track.state == TrackState.LOST:
                    continue

                color = self.COLOR_MAP.get(track.class_name, self.COLOR_MAP["DEFAULT"])
                if track.state == TrackState.TEMPORARILY_LOST:
                    color = tuple(int(c * 0.5) for c in color)  # type: ignore

                bx1, by1 = int(track.bbox.x1), int(track.bbox.y1)
                bx2, by2 = int(track.bbox.x2), int(track.bbox.y2)

                # Bounding Box
                cv2.rectangle(vis, (bx1, by1), (bx2, by2), color, 2, cv2.LINE_AA)

                # Label Badge
                label_parts = []
                if self.config.show_tracks:
                    label_parts.append(f"#{track.track_id}")
                label_parts.append(track.class_name)
                if self.config.show_confidence:
                    label_parts.append(f"{track.confidence:.2f}")
                if track.state == TrackState.TEMPORARILY_LOST:
                    label_parts.append("[OCCLUDED]")

                label = " ".join(label_parts)
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                cv2.rectangle(vis, (bx1, max(0, by1 - lh - 6)), (bx1 + lw + 6, max(lh + 6, by1)), color, -1)
                cv2.putText(vis, label, (bx1 + 3, max(lh, by1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)

                # Dynamic Alpha-Fading Trajectory Trail (Breadcrumb trail)
                if len(track.history) > 1:
                    hist = track.history
                    n_pts = len(hist)
                    for idx in range(1, n_pts):
                        pt1 = (int(hist[idx - 1][0]), int(hist[idx - 1][1]))
                        pt2 = (int(hist[idx][0]), int(hist[idx][1]))
                        progress = idx / float(n_pts)
                        # Brightness fades gracefully toward the oldest tail point
                        faded_color = tuple(int(c * (0.25 + 0.75 * progress)) for c in color)
                        thickness = 1 if progress < 0.6 else 2
                        cv2.line(vis, pt1, pt2, faded_color, thickness, cv2.LINE_AA)
                    # Glowing point at current head of trail
                    cv2.circle(vis, (int(hist[-1][0]), int(hist[-1][1])), 3, color, -1, cv2.LINE_AA)

        # 2. Render 33-Keypoint Glowing Skeleton
        if self.config.show_pose:
            for pose in state.poses:
                kp_dict = {kp.name.lower(): (int(kp.x), int(kp.y)) for kp in pose.keypoints if kp.name}

                # Select bone list based on number of keypoints
                is_mediapipe = len(pose.keypoints) > 15
                bones = self.BLAZEPOSE_BONES if is_mediapipe else self.LEGACY_POSE_CONNECTIONS

                # Draw bone connecting lines
                for pt1_name, pt2_name, bone_color, thickness in bones:
                    if pt1_name in kp_dict and pt2_name in kp_dict:
                        p1 = kp_dict[pt1_name]
                        p2 = kp_dict[pt2_name]
                        cv2.line(vis, p1, p2, bone_color, thickness, cv2.LINE_AA)

                # Draw glowing joint nodes
                for kp in pose.keypoints:
                    if not kp.name:
                        continue
                    px, py = int(kp.x), int(kp.y)
                    name_l = kp.name.lower()
                    is_hand_node = "wrist" in name_l or "pinky" in name_l or "index" in name_l or "thumb" in name_l
                    if "left" in name_l and is_hand_node:
                        node_col = (214, 112, 218)
                    elif "right" in name_l and is_hand_node:
                        node_col = (0, 165, 255)
                    elif "eye" in name_l or "ear" in name_l or "nose" in name_l:
                        node_col = (0, 229, 255)
                    else:
                        node_col = (0, 230, 118)

                    cv2.circle(vis, (px, py), 4, node_col, -1, cv2.LINE_AA)
                    cv2.circle(vis, (px, py), 6, (255, 255, 255), 1, cv2.LINE_AA)

                # Orientation / Roll angle indicator
                if pose.bbox and pose.orientation_angle is not None:
                    roll_deg = math.degrees(pose.orientation_angle)
                    angle_text = f"ROLL: {roll_deg:+.1f} deg"
                    cv2.putText(vis, angle_text, (int(pose.bbox.x1), int(pose.bbox.y2 + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 229, 255), 1, cv2.LINE_AA)

        # 3. Render Hand Reticles, Crosshairs & Finger Web
        active_hand_points: List[Tuple[int, int]] = []
        if self.config.show_hands:
            for hand in state.hands:
                wx, wy = int(hand.wrist[0]), int(hand.wrist[1])
                is_left = hand.hand_type.value == "LEFT"
                hand_color = (214, 112, 218) if is_left else (0, 165, 255)

                active_hand_points.append((wx, wy))

                # Concentric targeting reticle & crosshairs at wrist
                cv2.circle(vis, (wx, wy), 9, hand_color, 2, cv2.LINE_AA)
                cv2.circle(vis, (wx, wy), 15, hand_color, 1, cv2.LINE_AA)
                cv2.line(vis, (wx - 10, wy), (wx + 10, wy), hand_color, 1, cv2.LINE_AA)
                cv2.line(vis, (wx, wy - 10), (wx, wy + 10), hand_color, 1, cv2.LINE_AA)

                # Finger skeletal web and palm center
                kp_dict = {kp.name.lower(): (int(kp.x), int(kp.y)) for kp in hand.keypoints if kp.name}
                if "palm_center" in kp_dict:
                    px, py = kp_dict["palm_center"]
                    cv2.circle(vis, (px, py), 5, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(vis, (px, py), 5, hand_color, 1, cv2.LINE_AA)

                for fname in ["thumb", "index", "pinky", "primary_fingertip"]:
                    if fname in kp_dict:
                        fx, fy = kp_dict[fname]
                        cv2.line(vis, (wx, wy), (fx, fy), hand_color, 1, cv2.LINE_AA)
                        cv2.circle(vis, (fx, fy), 3, (255, 255, 255), -1, cv2.LINE_AA)

                # Hand badge
                if hand.bbox:
                    bx1, by1 = int(hand.bbox.x1), int(hand.bbox.y1)
                    hand_tag = f"{hand.hand_type.value} HAND"
                    (tw, th), _ = cv2.getTextSize(hand_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                    cv2.rectangle(vis, (bx1, max(0, by1 - th - 6)), (bx1 + tw + 6, max(th + 6, by1)), (20, 20, 20), -1)
                    cv2.rectangle(vis, (bx1, max(0, by1 - th - 6)), (bx1 + tw + 6, max(th + 6, by1)), hand_color, 1)
                    cv2.putText(vis, hand_tag, (bx1 + 3, max(th, by1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, hand_color, 1, cv2.LINE_AA)

        # 4. Laser Targeting Guide Lines (Proximity Beam to closest target)
        if self.config.show_laser_guides and active_hand_points:
            active_objects = [t for t in state.tracks if t.is_active and t.class_name.upper() != "ASTRONAUT"]
            for hx, hy in active_hand_points:
                for obj in active_objects:
                    ox, oy = int(obj.center[0]), int(obj.center[1])
                    dist_px = float(np.hypot(hx - ox, hy - oy))
                    # Draw guide beam if within approach threshold (< 220 pixels)
                    if dist_px < 220.0:
                        beam_col = (0, 229, 255) if "RED" in obj.class_name else (0, 140, 255)
                        cv2.line(vis, (hx, hy), (ox, oy), beam_col, 1, cv2.LINE_AA)
                        cv2.circle(vis, (ox, oy), 16, beam_col, 1, cv2.LINE_AA)
                        cv2.circle(vis, (ox, oy), 8, beam_col, -1, cv2.LINE_AA)

        # 5. Translucent Cyber-Aerospace Telemetry HUD
        if self.config.show_hud:
            overlay = vis.copy()
            hud_w = 270
            hud_h = 245
            hx, hy = 12, 12

            # Background translucent panel
            cv2.rectangle(overlay, (hx, hy), (hx + hud_w, hy + hud_h), (12, 16, 22), -1)
            cv2.rectangle(overlay, (hx, hy), (hx + hud_w, hy + hud_h), (0, 229, 255), 1)
            cv2.addWeighted(overlay, 0.82, vis, 0.18, 0, vis)

            # HUD Telemetry content
            ty = hy + 20
            # Header
            cv2.putText(vis, f"ASTRA-EA | {mode}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 230, 255), 1, cv2.LINE_AA)
            ty += 18
            cv2.line(vis, (hx + 8, ty - 4), (hx + hud_w - 8, ty - 4), (40, 65, 80), 1)

            # Subsystem status
            cv2.putText(vis, "OPTICAL SENSOR: ONLINE", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 128), 1)
            ty += 16
            cv2.putText(vis, "PERCEPTION:    ONLINE", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 128), 1)
            ty += 16
            act_tracks = [t for t in state.tracks if t.is_active]
            cv2.putText(vis, f"TRACKING:      ONLINE ({len(act_tracks)} act)", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 128), 1)
            ty += 16

            # Detector info
            det_label = "ColorSpatial" if "ColorSpatial" in self.config.detector_name else "YOLOv8"
            cv2.putText(vis, f"DETECTOR:      {det_label}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (230, 200, 70), 1)
            ty += 16

            # Targets & Persons
            person_str = str(state.persons[0].person_id) if state.persons else "STANDBY"
            cv2.putText(vis, f"PERSON:        {person_str}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (220, 220, 220), 1)
            ty += 16

            hand_count = len(state.hands)
            hand_desc = ", ".join(h.hand_type.value for h in state.hands) if hand_count > 0 else "NONE"
            cv2.putText(vis, f"HANDS:         {hand_desc}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (220, 220, 220), 1)
            ty += 16

            cv2.putText(vis, f"TARGET:        {target_name}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (220, 220, 220), 1)
            ty += 16

            cv2.putText(vis, f"INTERACT:      {interaction_state}", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 215, 255), 1)
            ty += 16

            cv2.putText(vis, f"ACTIVITY:      {activity_name} ({activity_confidence:.2f})", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 255, 120), 1)
            ty += 20

            # FPS and Latency
            lat = state.latency
            fps_color = (0, 255, 128) if state.fps >= 20.0 else (0, 180, 255)
            cv2.putText(vis, f"FPS: {state.fps:.1f}  LAT: {lat.total_ms:.1f}ms", (hx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.40, fps_color, 1, cv2.LINE_AA)

        # 6. Interactive Keyboard Controls Bar (Bottom)
        bot_y = h - 8
        bar_text = "[P]ose [H]ands [O]bjects [T]racks [I]nt [A]ct [D]ebug [E]vidence [R]eset [Q]uit"
        cv2.putText(vis, bar_text, (10, bot_y), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (160, 175, 190), 1, cv2.LINE_AA)

        return vis
