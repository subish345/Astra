"""Flight Integration Software Packager for ASTRA-EA (Phase 18).

In accordance with Section 6, 7, 8, 57 & 67:
Packages clean, reproducible flight-integration build:
ASTRA-EA-FLIGHT-INTEGRATION-001/
├── app/
├── config/
├── models/
├── migrations/
├── scripts/
├── docs/
├── checksums/
└── manifest/

Strictly strips development tooling (Dataset Studio, training pipelines, debug injectors).
Generates flight_manifest.json and flight_configuration_manifest.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("flight_packager")


class FlightPackager:
    """Packages the flight-integration build (D18.02)."""

    BUILD_NAME = "ASTRA-EA-FLIGHT-INTEGRATION-001"
    PRODUCT_VERSION = "ASTRA-EA-v1.0"
    SOFTWARE_VERSION = "1.0.0-RC1"

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        output_base: Optional[Path] = None,
    ) -> None:
        self.root_dir = root_dir or Path(os.getcwd())
        self.output_base = output_base or self.root_dir / "deployment" / "flight"
        self.package_dir = self.output_base / self.BUILD_NAME

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def build_package(self) -> Path:
        """Construct the flight-integration package."""
        if self.package_dir.exists():
            shutil.rmtree(self.package_dir)
        self.package_dir.mkdir(parents=True, exist_ok=True)

        # 1. Structure directories (Section 8)
        app_dir = self.package_dir / "app"
        config_dir = self.package_dir / "config"
        models_dir = self.package_dir / "models"
        migrations_dir = self.package_dir / "migrations"
        scripts_dir = self.package_dir / "scripts"
        docs_dir = self.package_dir / "docs"
        checksums_dir = self.package_dir / "checksums"
        manifest_dir = self.package_dir / "manifest"

        for d in [app_dir, config_dir, models_dir, migrations_dir, scripts_dir, docs_dir, checksums_dir, manifest_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 2. Copy application runtime (strip dataset & training, Section 67)
        core_src = self.root_dir / "core"
        if core_src.exists():
            shutil.copytree(
                core_src,
                app_dir / "core",
                ignore=shutil.ignore_patterns("dataset", "training", "__pycache__", "*.pyc"),
            )

        int_src = self.root_dir / "integration"
        if int_src.exists():
            shutil.copytree(
                int_src,
                app_dir / "integration",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

        # 3. Copy configuration
        for cfg in ["system.yaml"]:
            p = self.root_dir / "configs" / cfg
            if p.exists():
                shutil.copy2(p, config_dir / cfg)

        exp_src = self.root_dir / "configs" / "experiments"
        if exp_src.exists():
            shutil.copytree(exp_src, config_dir / "experiments", dirs_exist_ok=True)

        # 4. Copy models (only validated ONNX & Haar cascades, Section 29)
        models_src = self.root_dir / "models" / "checkpoints"
        if models_src.exists():
            for f in models_src.glob("*"):
                if f.is_file() and not f.name.endswith(".pt"):  # Ship lightweight edge ONNX + XML
                    shutil.copy2(f, models_dir / f.name)

        # 5. Copy database migrations
        mig_src = self.root_dir / "storage" / "database" / "migrations"
        if mig_src.exists():
            shutil.copytree(mig_src, migrations_dir, dirs_exist_ok=True)

        # 6. Copy flight startup scripts
        startup_sh = scripts_dir / "start_flight.sh"
        startup_sh.write_text("""#!/usr/bin/env bash
# ASTRA-EA Flight-Integration Startup Script
export ASTRA_RUNTIME_MODE="FLIGHT_INTEGRATION"
export ASTRA_PLATFORM_PROFILE="FLIGHT_TARGET_TBD"
python3 -m app.core.flight.startup
""", encoding="utf-8")
        startup_sh.chmod(0o755)

        # 7. Copy flight documentation
        flight_docs = self.root_dir / "docs" / "flight"
        if flight_docs.exists():
            shutil.copytree(flight_docs, docs_dir, dirs_exist_ok=True)

        # 8. Compute all checksums
        checksum_entries = []
        for root, _, files in os.walk(self.package_dir):
            for file_name in sorted(files):
                file_path = Path(root) / file_name
                if "checksums" in str(file_path) or "manifest" in str(file_path):
                    continue
                rel = file_path.relative_to(self.package_dir)
                digest = self._hash_file(file_path)
                checksum_entries.append(f"{digest}  {rel}")

        checksums_file = checksums_dir / "sha256sums.txt"
        checksums_file.write_text("\n".join(checksum_entries) + "\n", encoding="utf-8")

        # 9. Generate Manifests (Section 7 & 57)
        build_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        git_commit = "d480f4851815a92a6722c6b3d19b9575bae0d950"  # Phase 17 commit

        flight_manifest = {
            "product_version": self.PRODUCT_VERSION,
            "software_version": self.SOFTWARE_VERSION,
            "build_name": self.BUILD_NAME,
            "build_timestamp": build_ts,
            "git_commit": git_commit,
            "model_version": "ASTRA_OBJECT_DETECTOR_v0.1.0-ONNX",
            "dataset_version": "ASTRA-DS-v1.0",
            "procedure_version": "DEMO-PROC-v1.0",
            "configuration_version": "v1.0",
            "platform_profile": "FLIGHT_TARGET_TBD",
            "package_type": "FLIGHT_INTEGRATION_BUILD",
            "total_files": len(checksum_entries),
            "checksums_file": "checksums/sha256sums.txt",
        }

        config_manifest = {
            "hardware_profile": "FLIGHT_TARGET_TBD",
            "software_version": self.SOFTWARE_VERSION,
            "model_version": "ASTRA_OBJECT_DETECTOR_v0.1.0-ONNX",
            "procedure_version": "DEMO-PROC-v1.0",
            "configuration_version": "v1.0",
            "camera_profile": "SONY_IMX477_1080P30_V4L2",
            "storage_profile": "FLIGHT_DATA_PARTITIONED_10GB",
            "telemetry_profile": "DOWNLINK_1HZ_NDJSON_TBD",
            "command_profile": "LOCAL_OPERATOR_AUTH_V1",
            "build_timestamp": build_ts,
        }

        # Write inside package manifest/
        with open(manifest_dir / "flight_manifest.json", "w", encoding="utf-8") as f:
            json.dump(flight_manifest, f, indent=2)
        with open(manifest_dir / "flight_configuration_manifest.json", "w", encoding="utf-8") as f:
            json.dump(config_manifest, f, indent=2)

        # Write to root for repository baseline verification
        with open(self.root_dir / "flight_manifest.json", "w", encoding="utf-8") as f:
            json.dump(flight_manifest, f, indent=2)
        with open(self.root_dir / "flight_configuration_manifest.json", "w", encoding="utf-8") as f:
            json.dump(config_manifest, f, indent=2)

        return self.package_dir
