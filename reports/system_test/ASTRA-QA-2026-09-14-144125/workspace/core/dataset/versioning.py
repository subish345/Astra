"""Dataset Version Manager for ASTRA-EA.

Creates, registers, and loads immutable dataset versions and manifests
(e.g., ASTRA-DATASET-v0.1, ASTRA-DATASET-v0.2).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.dataset.schema import DatasetManifest, DatasetSplit


class DatasetVersionManager:
    """Manages versioned dataset manifests and registry."""

    def __init__(
        self,
        manifests_dir: str = "datasets/manifests",
        versions_dir: str = "datasets/versions",
    ) -> None:
        self.manifests_dir = Path(manifests_dir)
        self.versions_dir = Path(versions_dir)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def create_version(
        self,
        dataset_id: str,
        version: str,
        dataset_dir: str,
        experiment: str = "DEMO_EXP_001",
        source: str = "HYBRID",
        classes: Optional[List[str]] = None,
        generator_version: Optional[str] = None,
    ) -> DatasetManifest:
        """Scan a dataset directory and build/register a versioned manifest."""
        ds_path = Path(dataset_dir)
        annos_dir = ds_path / "annotations"
        if not annos_dir.exists():
            annos_dir = ds_path

        anno_files = list(annos_dir.glob("*.json"))
        anno_files = [
            p for p in anno_files
            if not p.name.startswith("dataset_") and p.name not in {"index.json", "metadata.json"}
        ]

        # Scan annotations to gather statistics
        sessions: set[str] = set()
        camera_profiles: set[str] = set()
        scenarios: set[str] = set()
        sample_ids: list[str] = []

        for f in anno_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                sample_ids.append(data.get("sample_id", f.stem))
                if "session_id" in data:
                    sessions.add(data["session_id"])
                if "camera_profile" in data:
                    camera_profiles.add(data["camera_profile"])
                if "scenario" in data:
                    scenarios.add(data["scenario"])
            except Exception:
                pass

        # Check for existing splits
        splits = DatasetSplit()
        split_summary_path = ds_path / "splits" / "split_summary.json"
        if split_summary_path.exists():
            try:
                with open(split_summary_path, "r", encoding="utf-8") as fp:
                    split_info = json.load(fp)
                # Load sample IDs from train.txt, validation.txt, test.txt
                train_file = ds_path / "splits" / "train.txt"
                val_file = ds_path / "splits" / "validation.txt"
                test_file = ds_path / "splits" / "test.txt"
                if train_file.exists():
                    splits.train = [l.strip() for l in train_file.read_text(encoding="utf-8").splitlines() if l.strip()]
                if val_file.exists():
                    splits.validation = [l.strip() for l in val_file.read_text(encoding="utf-8").splitlines() if l.strip()]
                if test_file.exists():
                    splits.test = [l.strip() for l in test_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            except Exception:
                pass

        default_classes = ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"]
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            version=version,
            created_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            experiment=experiment,
            classes=classes or default_classes,
            sample_count=len(sample_ids),
            session_count=len(sessions),
            camera_profiles=sorted(list(camera_profiles)),
            scenarios=sorted(list(scenarios)),
            annotation_schema="ASTRA_DETECTION_v1",
            generator_version=generator_version,
            splits=splits,
            provenance={
                "dataset_directory": str(ds_path),
                "sessions": sorted(list(sessions)),
            },
        )

        # Save manifest to manifests/ and directly in the dataset directory
        manifest_file = self.manifests_dir / f"{dataset_id}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        local_manifest = ds_path / "dataset_manifest.json"
        with open(local_manifest, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        # Register in versions registry
        registry_file = self.versions_dir / "registry.json"
        registry: Dict[str, Any] = {}
        if registry_file.exists():
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}

        registry[dataset_id] = {
            "version": version,
            "created_at": manifest.created_at,
            "sample_count": manifest.sample_count,
            "session_count": manifest.session_count,
            "manifest_path": str(manifest_file),
            "dataset_directory": str(ds_path),
        }

        with open(registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        return manifest

    def load_manifest(self, dataset_id: str) -> Optional[DatasetManifest]:
        """Load manifest by dataset ID."""
        manifest_file = self.manifests_dir / f"{dataset_id}.json"
        if not manifest_file.exists():
            # Check local file or registry
            return None
        with open(manifest_file, "r", encoding="utf-8") as f:
            return DatasetManifest.model_validate_json(f.read())

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all registered dataset versions."""
        registry_file = self.versions_dir / "registry.json"
        if not registry_file.exists():
            return []
        with open(registry_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [{"dataset_id": k, **v} for k, v in data.items()]
