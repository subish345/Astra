"""Dataset Studio Foundation for ASTRA-EA.

Unifies dataset recording, procedural synthesis, schema validation,
session-level splitting, version management, and reporting into a cohesive API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.dataset.generator import SyntheticDatasetGenerator
from core.dataset.recorder import DatasetSessionRecorder
from core.dataset.reporter import DatasetReporter
from core.dataset.schema import DatasetManifest, DatasetSplit
from core.dataset.splitter import DatasetSplitter
from core.dataset.validator import DatasetValidator
from core.dataset.versioning import DatasetVersionManager


class DatasetStudio:
    """High-level facade orchestrating all dataset operations."""

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.root = Path(workspace_root) if workspace_root else Path.cwd()
        self.raw_dir = self.root / "datasets" / "raw"
        self.synthetic_dir = self.raw_dir / "synthetic"
        self.real_dir = self.raw_dir / "real"
        self.manifests_dir = self.root / "datasets" / "manifests"
        self.versions_dir = self.root / "datasets" / "versions"
        self.reports_dir = self.root / "datasets" / "reports"

        # Ensure base directories exist
        for d in [self.raw_dir, self.synthetic_dir, self.real_dir, self.manifests_dir, self.versions_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.version_manager = DatasetVersionManager(
            manifests_dir=str(self.manifests_dir),
            versions_dir=str(self.versions_dir),
        )

    def record_session(
        self,
        source: str = "0",
        session_id: Optional[str] = None,
        experiment_id: str = "DEMO_EXP_001",
        camera_profile: str = "VIEW_LEFT",
        scenario: str = "CORRECT",
        operator_id: Optional[str] = None,
        notes: str = "",
        max_frames: Optional[int] = None,
        max_duration_sec: Optional[float] = None,
        interactive_display: bool = False,
    ) -> Dict[str, Any]:
        """Record real camera session into datasets/raw/real/."""
        recorder = DatasetSessionRecorder(base_dir=str(self.real_dir))
        return recorder.record_session(
            source=source,
            session_id=session_id,
            experiment_id=experiment_id,
            camera_profile=camera_profile,
            scenario=scenario,
            operator_id=operator_id,
            notes=notes,
            max_frames=max_frames,
            max_duration_sec=max_duration_sec,
            interactive_display=interactive_display,
        )

    def synthesize(
        self,
        output_dir: Optional[str] = None,
        sample_count: int = 100,
        seed: int = 12345,
        experiment_id: str = "DEMO_EXP_001",
        camera_profiles: Optional[List[str]] = None,
        scenarios: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate synthetic dataset with controlled variations and ground truth."""
        out = output_dir or str(self.synthetic_dir / "demo_synthetic")
        generator = SyntheticDatasetGenerator(
            output_dir=out,
            experiment_id=experiment_id,
        )
        return generator.generate_dataset(
            sample_count=sample_count,
            seed=seed,
            camera_profiles=camera_profiles,
            scenarios=scenarios,
        )

    def validate(
        self,
        dataset_path: str,
        manifest_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate dataset files, bounding boxes, and verify zero cross-split leakage."""
        validator = DatasetValidator(dataset_dir=dataset_path)
        return validator.validate(manifest_path=manifest_path)

    def split(
        self,
        dataset_path: str,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> DatasetSplit:
        """Partition dataset at session level into train, validation, and test."""
        splitter = DatasetSplitter(
            dataset_dir=dataset_path,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )
        return splitter.split_dataset()

    def version(
        self,
        dataset_id: str,
        version: str,
        dataset_path: str,
        experiment: str = "DEMO_EXP_001",
        source: str = "HYBRID",
    ) -> DatasetManifest:
        """Register an immutable versioned dataset manifest."""
        return self.version_manager.create_version(
            dataset_id=dataset_id,
            version=version,
            dataset_dir=dataset_path,
            experiment=experiment,
            source=source,
        )

    def report(
        self,
        dataset_path: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate dataset distribution, balance, and quality reports."""
        reporter = DatasetReporter(dataset_dir=dataset_path)
        return reporter.generate_report(output_dir=output_dir)

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all versioned datasets registered in the system."""
        return self.version_manager.list_versions()
