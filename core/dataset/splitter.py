"""Session-Level Dataset Splitter.

Splits dataset samples across Train (70%), Validation (15%), and Test (15%)
strictly by session/recording boundary to guarantee zero temporal data leakage.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.dataset.schema import DatasetManifest, DatasetSplit, FrameDetectionAnnotation


class DatasetSplitter:
    """Partitions samples into train, val, and test splits strictly by session."""

    def __init__(
        self,
        dataset_dir: str,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        total_ratio = train_ratio + val_ratio + test_ratio
        self.train_ratio = train_ratio / total_ratio
        self.val_ratio = val_ratio / total_ratio
        self.test_ratio = test_ratio / total_ratio
        self.seed = seed

    def split_dataset(
        self,
        manifest_path: Optional[str] = None,
        save_splits_dir: Optional[str] = None,
    ) -> DatasetSplit:
        """Partition sessions and update dataset manifest."""
        annos_dir = self.dataset_dir / "annotations"
        if not annos_dir.exists():
            annos_dir = self.dataset_dir

        anno_files = list(annos_dir.glob("*.json"))
        anno_files = [
            p for p in anno_files
            if not p.name.startswith("dataset_") and p.name not in {"index.json", "metadata.json"}
        ]

        if not anno_files:
            raise ValueError(f"No annotation samples found in '{annos_dir}' to split.")

        # Group sample IDs by session ID
        session_to_samples: Dict[str, List[str]] = {}
        for f in sorted(anno_files):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                sample_id = data.get("sample_id", f.stem)
                sess_id = data.get("session_id", "DEFAULT_SESSION")
                session_to_samples.setdefault(sess_id, []).append(sample_id)
            except Exception:
                continue

        unique_sessions = sorted(list(session_to_samples.keys()))
        rng = random.Random(self.seed)
        rng.shuffle(unique_sessions)

        num_sessions = len(unique_sessions)
        if num_sessions < 3:
            # When session count is small, allocate at least 1 session to each if possible
            train_sessions = unique_sessions[:1]
            val_sessions = unique_sessions[1:2] if num_sessions > 1 else []
            test_sessions = unique_sessions[2:] if num_sessions > 2 else []
        else:
            n_train = max(1, int(round(num_sessions * self.train_ratio)))
            n_val = max(1, int(round(num_sessions * self.val_ratio)))
            # Ensure at least 1 session in test
            if n_train + n_val >= num_sessions:
                n_train = max(1, num_sessions - 2)
                n_val = 1

            train_sessions = unique_sessions[:n_train]
            val_sessions = unique_sessions[n_train : n_train + n_val]
            test_sessions = unique_sessions[n_train + n_val :]
            if not test_sessions and num_sessions >= 3:
                test_sessions = [val_sessions.pop()]

        # Collect sample IDs
        train_samples: List[str] = []
        val_samples: List[str] = []
        test_samples: List[str] = []

        for s in train_sessions:
            train_samples.extend(session_to_samples[s])
        for s in val_sessions:
            val_samples.extend(session_to_samples[s])
        for s in test_sessions:
            test_samples.extend(session_to_samples[s])

        split = DatasetSplit(
            train=train_samples,
            validation=val_samples,
            test=test_samples,
        )

        # Update or create dataset_manifest.json
        manifest_file = Path(manifest_path) if manifest_path else self.dataset_dir / "dataset_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = DatasetManifest.model_validate_json(f.read())
                manifest.splits = split
                with open(manifest_file, "w", encoding="utf-8") as f:
                    f.write(manifest.model_dump_json(indent=2))
            except Exception:
                pass

        # Also write explicit split files in splits/ if requested or in datasets/splits/
        splits_target_dir = Path(save_splits_dir) if save_splits_dir else self.dataset_dir / "splits"
        splits_target_dir.mkdir(parents=True, exist_ok=True)

        for split_name, s_list in [("train", train_samples), ("validation", val_samples), ("test", test_samples)]:
            with open(splits_target_dir / f"{split_name}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(s_list) + "\n")

        with open(splits_target_dir / "split_summary.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_samples": len(train_samples) + len(val_samples) + len(test_samples),
                    "total_sessions": num_sessions,
                    "train_sessions": train_sessions,
                    "train_samples": len(train_samples),
                    "val_sessions": val_sessions,
                    "val_samples": len(val_samples),
                    "test_sessions": test_sessions,
                    "test_samples": len(test_samples),
                    "seed": self.seed,
                },
                f,
                indent=2,
            )

        return split
