"""Comprehensive debug visualizer for activities, interactions, and temporal timelines.

Renders active primitives, composite activity badges, confidence meters,
and a rolling temporal action timeline at the base of the frame.
"""

from __future__ import annotations

from typing import List, Optional
import cv2
import numpy as np

from core.activity.types import ActivityObservation, ActivityStatus
from core.interaction.types import InteractionEvent
from core.interaction.visualizer import InteractionVisualizer

STATUS_COLORS = {
    ActivityStatus.CONFIRMED: (0, 255, 0),     # Bright Green
    ActivityStatus.IN_PROGRESS: (0, 215, 255), # Amber
    ActivityStatus.UNCERTAIN: (0, 165, 255),   # Orange
    ActivityStatus.CANCELLED: (0, 0, 255),     # Red
    ActivityStatus.ENDED: (128, 128, 128),     # Gray
}


class ActivityVisualizer:
    """Renders activities, confidence indicators, and temporal timeline onto video frames."""

    @classmethod
    def render(
        cls,
        image: np.ndarray,
        interactions: List[InteractionEvent],
        primitives: List[ActivityObservation],
        composites: List[ActivityObservation],
        timeline_history: Optional[List[ActivityObservation]] = None,
    ) -> np.ndarray:
        """Annotate frame with complete Phase 3 interaction and activity diagnostics."""
        # 1. Base interaction vectors
        vis = InteractionVisualizer.render(image, interactions, show_hud=False)
        h, w = vis.shape[:2]

        # 2. Activity Diagnostics Panel (Top-Right)
        panel_w = 280
        panel_h = 130
        px1 = w - panel_w - 15
        py1 = 15
        cv2.rectangle(vis, (px1, py1), (w - 15, py1 + panel_h), (25, 25, 25), -1)
        cv2.rectangle(vis, (px1, py1), (w - 15, py1 + panel_h), (80, 80, 80), 1)

        cv2.putText(vis, "ACTIVITY RECOGNITION (PHASE 3)", (px1 + 10, py1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 215, 255), 1, cv2.LINE_AA)

        # Draw active composite or primitive
        curr_act = composites[0] if composites else (primitives[0] if primitives else None)
        if curr_act:
            st_color = STATUS_COLORS.get(curr_act.status, (255, 255, 255))
            act_text = f"ACTION: {curr_act.activity_name}"
            cv2.putText(vis, act_text, (px1 + 10, py1 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, st_color, 2, cv2.LINE_AA)

            stat_text = f"STATUS: {curr_act.status.value} | {curr_act.confidence_level.value}"
            cv2.putText(vis, stat_text, (px1 + 10, py1 + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

            # Confidence bar
            conf_w = int(220 * curr_act.confidence)
            cv2.rectangle(vis, (px1 + 10, py1 + 80), (px1 + 230, py1 + 92), (50, 50, 50), -1)
            cv2.rectangle(vis, (px1 + 10, py1 + 80), (px1 + 10 + conf_w, py1 + 92), st_color, -1)
            cv2.putText(vis, f"{curr_act.confidence:.2f}", (px1 + 235, py1 + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            prim_sub = " > ".join(curr_act.primitives[-3:]) if curr_act.primitives else "NONE"
            cv2.putText(vis, f"Trace: {prim_sub}", (px1 + 10, py1 + 112), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)
        else:
            cv2.putText(vis, "ACTION: IDLE", (px1 + 10, py1 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (160, 160, 160), 1, cv2.LINE_AA)
            cv2.putText(vis, "No active activity detected", (px1 + 10, py1 + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 120, 120), 1, cv2.LINE_AA)

        # 3. Rolling Temporal Timeline (Bottom Bar)
        if timeline_history:
            bar_h = 30
            bar_y = h - bar_h - 10
            bar_x1 = 20
            bar_x2 = w - 20
            bar_len = bar_x2 - bar_x1

            cv2.rectangle(vis, (bar_x1, bar_y), (bar_x2, bar_y + bar_h), (20, 20, 20), -1)
            cv2.rectangle(vis, (bar_x1, bar_y), (bar_x2, bar_y + bar_h), (70, 70, 70), 1)
            cv2.putText(vis, "TIMELINE (5s)", (bar_x1 + 5, bar_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)

            # Draw blocks for recent activities in history (most recent on right)
            total_items = min(15, len(timeline_history))
            if total_items > 0:
                slot_w = bar_len / float(total_items)
                for idx, item in enumerate(timeline_history[-total_items:]):
                    bx1 = int(bar_x1 + idx * slot_w)
                    bx2 = int(bx1 + slot_w - 2)
                    c = STATUS_COLORS.get(item.status, (150, 150, 150))
                    cv2.rectangle(vis, (bx1, bar_y + 4), (bx2, bar_y + bar_h - 4), c, -1)
                    label = item.activity_name[:3]
                    cv2.putText(vis, label, (bx1 + 2, bar_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1, cv2.LINE_AA)

        return vis
