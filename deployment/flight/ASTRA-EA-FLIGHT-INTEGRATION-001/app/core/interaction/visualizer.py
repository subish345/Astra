"""Visualization overlay for hand-object physical interactions.

Renders spatial vectors, kinematic states, and interaction HUD badges on RGB frames.
"""

from __future__ import annotations

from typing import List, Tuple
import cv2
import numpy as np

from core.interaction.types import InteractionEvent, InteractionState

# State color palette (BGR)
STATE_COLORS = {
    InteractionState.NONE: (160, 160, 160),
    InteractionState.APPROACHING: (0, 215, 255),  # Yellow-Amber
    InteractionState.NEAR: (255, 191, 0),        # Cyan-Blue
    InteractionState.CONTACT: (0, 140, 255),     # Orange
    InteractionState.GRASPING: (180, 105, 255),  # Pink-Magenta
    InteractionState.HOLDING: (0, 255, 0),       # Green
    InteractionState.MOVING: (50, 205, 50),      # Lime Green
    InteractionState.RELEASING: (0, 0, 255),     # Red
    InteractionState.RELEASED: (128, 0, 128),    # Purple
}


class InteractionVisualizer:
    """Renders interaction states and spatial vectors onto video frames."""

    @classmethod
    def render(
        cls,
        image: np.ndarray,
        interactions: List[InteractionEvent],
        show_hud: bool = True,
    ) -> np.ndarray:
        """Annotate frame with interaction vectors, state lines, and HUD indicators."""
        vis = image.copy()

        y_offset = 120  # Below standard perception header

        for event in interactions:
            if event.state == InteractionState.NONE and not event.is_uncertain:
                continue

            color = STATE_COLORS.get(event.state, (200, 200, 200))

            if event.spatial:
                hx, hy = int(event.spatial.hand_center[0]), int(event.spatial.hand_center[1])
                ox, oy = int(event.spatial.object_center[0]), int(event.spatial.object_center[1])

                # 1. Draw interaction coupling line
                thickness = 3 if event.state in (InteractionState.GRASPING, InteractionState.HOLDING, InteractionState.MOVING) else 2
                cv2.line(vis, (hx, hy), (ox, oy), color, thickness, cv2.LINE_AA)

                # 2. Draw midpoint distance badge
                mx, my = (hx + ox) // 2, (hy + oy) // 2
                label = f"{event.state.value} ({event.spatial.normalized_distance:.2f})"
                cv2.circle(vis, (mx, my), 4, color, -1)
                cv2.putText(vis, label, (mx + 8, my - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(vis, label, (mx + 8, my - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

            # 3. HUD status line
            if show_hud:
                hud_text = (
                    f"INT: {event.hand_type} -> {event.target_object_id}#{event.target_track_id} | "
                    f"STATE: {event.state.value} ({event.confidence:.2f}) | "
                    f"DUR: {event.duration_seconds:.1f}s"
                )
                if event.is_uncertain:
                    hud_text += " [UNCERTAIN]"

                cv2.rectangle(vis, (10, y_offset - 16), (480, y_offset + 6), (20, 20, 20), -1)
                cv2.rectangle(vis, (10, y_offset - 16), (480, y_offset + 6), color, 1)
                cv2.putText(vis, hud_text, (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
                y_offset += 26

        return vis
