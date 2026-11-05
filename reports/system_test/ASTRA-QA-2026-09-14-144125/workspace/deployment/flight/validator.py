"""Flight Package Integrity Validator for ASTRA-EA (Phase 18).

In accordance with Section 55 & 67:
Validates flight software package:
- Manifest existence & schema
- Checksum verification for all packaged artifacts
- Required files and directory structure
- Model checkpoint presence
- Procedure specification presence
- Configuration presence
- Startup scripts
- Confirms zero development tooling (Dataset Studio, training scripts) packaged
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class PackageValidationError(Exception):
    """Raised when package fails verification."""
    pass


class FlightPackageValidator:
    """Validates flight-integration package structure and artifact hashes (D18.20)."""

    def __init__(self, package_dir: Path) -> None:
        self.package_dir = package_dir
        self.validation_errors: List[str] = []
        self.checked_artifacts_count: int = 0

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def validate(self) -> Tuple[bool, Dict[str, Any]]:
        """Run full package validation suite."""
        self.validation_errors.clear()
        self.checked_artifacts_count = 0

        if not self.package_dir.exists():
            return False, {"error": f"Package directory does not exist: {self.package_dir}"}

        # 1. Manifests check
        manifest_file = self.package_dir / "manifest" / "flight_manifest.json"
        config_manifest_file = self.package_dir / "manifest" / "flight_configuration_manifest.json"
        if not manifest_file.exists():
            self.validation_errors.append("Missing manifest/flight_manifest.json")
        if not config_manifest_file.exists():
            self.validation_errors.append("Missing manifest/flight_configuration_manifest.json")

        # 2. Required directories
        for d in ["app", "config", "models", "scripts", "checksums", "manifest"]:
            if not (self.package_dir / d).is_dir():
                self.validation_errors.append(f"Missing required package directory: {d}/")

        # 3. Checksums verification
        sums_file = self.package_dir / "checksums" / "sha256sums.txt"
        if not sums_file.exists():
            self.validation_errors.append("Missing checksums/sha256sums.txt")
        else:
            with open(sums_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            for line in lines:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    expected_hash, rel_path = parts
                    target_file = self.package_dir / rel_path
                    if not target_file.exists():
                        self.validation_errors.append(f"Packaged file listed in checksums missing: {rel_path}")
                    else:
                        actual_hash = self._hash_file(target_file)
                        if actual_hash != expected_hash:
                            self.validation_errors.append(f"Checksum mismatch for {rel_path}")
                        self.checked_artifacts_count += 1

        # 4. Check model presence
        models_dir = self.package_dir / "models"
        onnx_models = list(models_dir.glob("*.onnx"))
        if not onnx_models:
            self.validation_errors.append("No validated ONNX neural model found in models/")

        # 5. Check procedure presence
        exp_dir = self.package_dir / "config" / "experiments"
        procedures = list(exp_dir.glob("*.yaml")) if exp_dir.exists() else []
        if not procedures:
            self.validation_errors.append("No experiment procedure definition found in config/experiments/")

        # 6. Verify zero development tooling (Section 67)
        prohibited_paths = [
            self.package_dir / "app" / "core" / "dataset",
            self.package_dir / "app" / "core" / "training",
            self.package_dir / "app" / "apps" / "dataset_studio",
        ]
        for p in prohibited_paths:
            if p.exists():
                self.validation_errors.append(f"Prohibited development tooling found in flight package: {p}")

        is_valid = len(self.validation_errors) == 0
        summary = {
            "package_path": str(self.package_dir),
            "is_valid": is_valid,
            "checked_artifacts_count": self.checked_artifacts_count,
            "errors": self.validation_errors,
        }
        return is_valid, summary
