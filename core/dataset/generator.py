"""Synthetic Dataset Generator for ASTRA-EA.

Generates procedurally rendered experiment scenes with controlled variations
in lighting, viewpoint perspective, object positions, astronaut poses,
and occlusions, outputting exact ground-truth bounding box annotations
and provenance metadata.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.dataset.schema import (
    AnnotationSource,
    DetectedObjectAnnotation,
    FrameDetectionAnnotation,
    ScenarioType,
)


class SyntheticDatasetGenerator:
    """Procedural synthetic scene and ground-truth generator."""

    GENERATOR_VERSION = "0.1.0"
    DEFAULT_CLASSES = ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"]

    def __init__(
        self,
        output_dir: str = "datasets/raw/synthetic/demo_synthetic",
        experiment_id: str = "DEMO_EXP_001",
        width: int = 640,
        height: int = 480,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.experiment_id = experiment_id
        self.width = width
        self.height = height

    def generate_dataset(
        self,
        sample_count: int = 100,
        seed: int = 12345,
        camera_profiles: Optional[List[str]] = None,
        scenarios: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete synthetic dataset with reproducible seed."""
        # Set seeds for deterministic reproducibility
        random.seed(seed)
        np.random.seed(seed)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / "images"
        annos_dir = self.output_dir / "annotations"
        images_dir.mkdir(parents=True, exist_ok=True)
        annos_dir.mkdir(parents=True, exist_ok=True)

        profiles = camera_profiles or ["VIEW_LEFT", "VIEW_RIGHT"]
        active_scenarios = scenarios or [
            "CORRECT",
            "WRONG_OBJECT",
            "WRONG_ORDER",
            "SKIPPED",
            "INCOMPLETE",
            "UNCERTAIN",
            "RECOVERY",
        ]

        annotations: List[FrameDetectionAnnotation] = []
        class_counts: Dict[str, int] = {cls_name: 0 for cls_name in self.DEFAULT_CLASSES}

        # Divide samples across sessions (e.g. 5-10 sessions) to facilitate session-level splitting
        num_sessions = max(4, min(sample_count // 10, 20))
        samples_per_session = math.ceil(sample_count / num_sessions)

        sample_idx = 0
        for sess_num in range(num_sessions):
            session_id = f"SYNTH_SESS_{sess_num + 1:03d}"
            cam_profile = profiles[sess_num % len(profiles)]
            scenario = active_scenarios[sess_num % len(active_scenarios)]

            for in_sess_idx in range(samples_per_session):
                if sample_idx >= sample_count:
                    break

                sample_id = f"SYNTH_{sample_idx + 1:06d}"
                scene_seed = seed + sample_idx * 17

                # Generate single frame
                frame_img, frame_annos = self._render_scene(
                    sample_id=sample_id,
                    session_id=session_id,
                    camera_profile=cam_profile,
                    scenario=scenario,
                    scene_seed=scene_seed,
                    frame_seq=in_sess_idx,
                )

                img_filename = f"{sample_id}.jpg"
                img_path = images_dir / img_filename
                cv2.imwrite(str(img_path), frame_img)

                anno_filename = f"{sample_id}.json"
                anno_path = annos_dir / anno_filename

                frame_annos.image_path = f"images/{img_filename}"
                with open(anno_path, "w", encoding="utf-8") as f:
                    f.write(frame_annos.model_dump_json(indent=2))

                annotations.append(frame_annos)
                for obj in frame_annos.objects:
                    class_counts[obj.class_name] = class_counts.get(obj.class_name, 0) + 1

                sample_idx += 1

        # Write overall dataset index
        index_path = self.output_dir / "index.json"
        summary = {
            "dataset_name": self.output_dir.name,
            "generator_version": self.GENERATOR_VERSION,
            "seed": seed,
            "experiment_id": self.experiment_id,
            "sample_count": sample_idx,
            "session_count": num_sessions,
            "camera_profiles": profiles,
            "scenarios": active_scenarios,
            "classes": self.DEFAULT_CLASSES,
            "class_counts": class_counts,
        }
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

    def _render_scene(
        self,
        sample_id: str,
        session_id: str,
        camera_profile: str,
        scenario: str,
        scene_seed: int,
        frame_seq: int,
    ) -> Tuple[np.ndarray, FrameDetectionAnnotation]:
        """Render a single synthetic frame and compute ground-truth bounding boxes."""
        rng = random.Random(scene_seed)

        # 1. Base canvas (spacecraft laboratory interior)
        base_brightness = rng.randint(45, 80)
        img = np.full((self.height, self.width, 3), (base_brightness, base_brightness + 5, base_brightness + 10), dtype=np.uint8)

        # Draw workstation wall panels and grid
        for y in range(0, self.height, 60):
            cv2.line(img, (0, y), (self.width, y), (base_brightness + 15, base_brightness + 15, base_brightness + 20), 1)
        for x in range(0, self.width, 80):
            cv2.line(img, (x, 0), (x, self.height), (base_brightness + 15, base_brightness + 15, base_brightness + 20), 1)

        # 2. Lighting variations (lighting gradient & shadows)
        lighting_style = rng.choice(["BRIGHT", "NORMAL", "DIM", "SHADOW"])
        if lighting_style == "BRIGHT":
            img = cv2.add(img, np.full_like(img, 40))
        elif lighting_style == "DIM":
            img = cv2.subtract(img, np.full_like(img, 20))
        elif lighting_style == "SHADOW":
            # Cast diagonal shadow over left or right half
            shadow_mask = np.ones((self.height, self.width), dtype=np.float32)
            shadow_side = rng.choice(["left", "right"])
            if shadow_side == "left":
                shadow_mask[:, : self.width // 2] = 0.65
            else:
                shadow_mask[:, self.width // 2 :] = 0.65
            for c in range(3):
                img[:, :, c] = np.clip(img[:, :, c].astype(np.float32) * shadow_mask, 0, 255).astype(np.uint8)

        # Perspective shift according to camera viewpoint
        # VIEW_LEFT: Objects shifted slightly right, workstation angled
        # VIEW_RIGHT: Objects shifted slightly left
        x_offset = 35 if camera_profile == "VIEW_LEFT" else -35

        detected_objects: List[DetectedObjectAnnotation] = []

        # 3. Work surface
        ws_y1 = int(self.height * 0.58) + rng.randint(-10, 10)
        ws_y2 = self.height - 15
        ws_x1 = int(self.width * 0.10) + x_offset + rng.randint(-15, 15)
        ws_x2 = int(self.width * 0.90) + x_offset + rng.randint(-15, 15)
        ws_x1 = max(5, min(ws_x1, self.width - 100))
        ws_x2 = max(ws_x1 + 80, min(ws_x2, self.width - 5))

        # Render work surface
        cv2.rectangle(img, (ws_x1, ws_y1), (ws_x2, ws_y2), (90, 85, 80), -1)
        cv2.rectangle(img, (ws_x1, ws_y1), (ws_x2, ws_y2), (130, 125, 120), 2)
        detected_objects.append(
            DetectedObjectAnnotation(
                class_name="WORK_SURFACE",
                bbox=[float(ws_x1), float(ws_y1), float(ws_x2), float(ws_y2)],
                track_id=1,
                confidence=1.0,
            )
        )

        # 4. Main Box (Containment / Storage Unit)
        mb_w = rng.randint(90, 120)
        mb_h = rng.randint(70, 95)
        # Position toward one side of the workstation
        mb_x1 = ws_x1 + rng.randint(20, 70)
        mb_y1 = ws_y1 - mb_h + rng.randint(5, 25)
        mb_x2 = mb_x1 + mb_w
        mb_y2 = mb_y1 + mb_h

        # Render Main Box (Blue/Gray metallic enclosure)
        cv2.rectangle(img, (mb_x1, mb_y1), (mb_x2, mb_y2), (180, 110, 50), -1)
        cv2.rectangle(img, (mb_x1, mb_y1), (mb_x2, mb_y2), (220, 150, 90), 2)
        # Inner hatch
        cv2.rectangle(img, (mb_x1 + 10, mb_y1 + 10), (mb_x2 - 10, mb_y2 - 10), (140, 80, 30), 2)
        detected_objects.append(
            DetectedObjectAnnotation(
                class_name="MAIN_BOX",
                bbox=[float(mb_x1), float(mb_y1), float(mb_x2), float(mb_y2)],
                track_id=2,
                confidence=1.0,
            )
        )

        # 5. Red Specimen Box & Yellow Specimen Box
        box_w = rng.randint(38, 55)
        box_h = rng.randint(38, 55)

        # Positions depend on scenario
        if scenario == "WRONG_OBJECT":
            # Yellow box is in the active interaction focus zone
            y_box_x1 = ws_x1 + int((ws_x2 - ws_x1) * 0.45) + rng.randint(-15, 15)
            y_box_y1 = ws_y1 + rng.randint(15, 45)
            r_box_x1 = ws_x1 + int((ws_x2 - ws_x1) * 0.70) + rng.randint(-15, 15)
            r_box_y1 = ws_y1 + rng.randint(15, 45)
        else:
            # Normal or other scenarios: Red box is primary
            r_box_x1 = ws_x1 + int((ws_x2 - ws_x1) * 0.45) + rng.randint(-15, 15)
            r_box_y1 = ws_y1 + rng.randint(15, 45)
            y_box_x1 = ws_x1 + int((ws_x2 - ws_x1) * 0.75) + rng.randint(-15, 15)
            y_box_y1 = ws_y1 + rng.randint(15, 45)

        r_box_x2 = min(self.width - 5, r_box_x1 + box_w)
        r_box_y2 = min(self.height - 5, r_box_y1 + box_h)
        y_box_x2 = min(self.width - 5, y_box_x1 + box_w)
        y_box_y2 = min(self.height - 5, y_box_y1 + box_h)

        # Render Red Box (BGR: high Red, low Blue/Green)
        cv2.rectangle(img, (r_box_x1, r_box_y1), (r_box_x2, r_box_y2), (30, 30, 215), -1)
        cv2.rectangle(img, (r_box_x1, r_box_y1), (r_box_x2, r_box_y2), (50, 50, 255), 2)
        detected_objects.append(
            DetectedObjectAnnotation(
                class_name="RED_BOX",
                bbox=[float(r_box_x1), float(r_box_y1), float(r_box_x2), float(r_box_y2)],
                track_id=3,
                confidence=1.0,
            )
        )

        # Render Yellow Box (BGR: high Red + Green, low Blue)
        cv2.rectangle(img, (y_box_x1, y_box_y1), (y_box_x2, y_box_y2), (20, 210, 225), -1)
        cv2.rectangle(img, (y_box_x1, y_box_y1), (y_box_x2, y_box_y2), (40, 240, 255), 2)
        detected_objects.append(
            DetectedObjectAnnotation(
                class_name="YELLOW_BOX",
                bbox=[float(y_box_x1), float(y_box_y1), float(y_box_x2), float(y_box_y2)],
                track_id=4,
                confidence=1.0,
            )
        )

        # 6. Astronaut (Presence & Hand reaching/interacting)
        if scenario != "SKIPPED" or rng.random() > 0.4:
            # Astronaut torso/shoulder
            astro_cx = int(self.width * (0.28 if camera_profile == "VIEW_LEFT" else 0.72)) + rng.randint(-20, 20)
            astro_w = rng.randint(140, 180)
            astro_h = rng.randint(220, 300)
            astro_x1 = max(0, astro_cx - astro_w // 2)
            astro_x2 = min(self.width, astro_cx + astro_w // 2)
            astro_y1 = max(0, int(self.height * 0.12) + rng.randint(-15, 15))
            astro_y2 = min(self.height, astro_y1 + astro_h)

            # Draw Astronaut suit (White/Light Grey with blue NASA/ISRO-style patches)
            cv2.ellipse(
                img,
                (astro_cx, astro_y1 + astro_h // 2),
                (astro_w // 2, astro_h // 2),
                0,
                0,
                360,
                (210, 215, 220),
                -1,
            )
            cv2.circle(img, (astro_cx, astro_y1 + 45), 35, (160, 165, 170), -1)  # Helmet visor

            detected_objects.append(
                DetectedObjectAnnotation(
                    class_name="ASTRONAUT",
                    bbox=[float(astro_x1), float(astro_y1), float(astro_x2), float(astro_y2)],
                    track_id=5,
                    confidence=1.0,
                )
            )

            # Reaching Hand/Arm towards target specimen
            hand_target_x = r_box_x1 + box_w // 2 if scenario != "WRONG_OBJECT" else y_box_x1 + box_w // 2
            hand_target_y = r_box_y1 + box_h // 2 if scenario != "WRONG_OBJECT" else y_box_y1 + box_h // 2
            cv2.line(img, (astro_cx, astro_y1 + 90), (hand_target_x, hand_target_y), (195, 200, 205), 14)
            cv2.circle(img, (hand_target_x, hand_target_y), 16, (170, 175, 180), -1)

        # 7. Occlusion challenge (optional, for robustness)
        if scenario == "UNCERTAIN" or rng.random() < 0.15:
            occ_x1 = rng.randint(int(self.width * 0.3), int(self.width * 0.6))
            occ_y1 = rng.randint(int(self.height * 0.4), int(self.height * 0.7))
            occ_w = rng.randint(40, 80)
            occ_h = rng.randint(40, 80)
            cv2.rectangle(img, (occ_x1, occ_y1), (occ_x1 + occ_w, occ_y1 + occ_h), (50, 50, 50), -1)

        # Assemble FrameDetectionAnnotation
        frame_anno = FrameDetectionAnnotation(
            sample_id=sample_id,
            image_path="",  # Filled in caller
            session_id=session_id,
            camera_profile=camera_profile,
            scenario=ScenarioType(scenario),
            source=AnnotationSource.SYNTHETIC,
            width=self.width,
            height=self.height,
            timestamp=round(frame_seq * 0.033, 3),
            objects=detected_objects,
            metadata={
                "generator_version": self.GENERATOR_VERSION,
                "scene_seed": scene_seed,
                "experiment_id": self.experiment_id,
                "lighting_style": lighting_style,
            },
        )

        return img, frame_anno
