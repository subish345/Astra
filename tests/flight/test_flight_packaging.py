"""Automated Test Suite for Flight Software Packaging and Validation (Phase 18)."""

import pytest
from pathlib import Path

from deployment.flight.packager import FlightPackager
from deployment.flight.validator import FlightPackageValidator


def test_flight_packaging_and_validation(tmp_path):
    """Verify reproducible flight-integration packaging and checksum verification (Section 55)."""
    packager = FlightPackager(output_base=tmp_path)
    pkg_dir = packager.build_package()

    assert pkg_dir.exists()
    assert (pkg_dir / "manifest" / "flight_manifest.json").exists()
    assert (pkg_dir / "manifest" / "flight_configuration_manifest.json").exists()
    assert (pkg_dir / "checksums" / "sha256sums.txt").exists()
    assert (pkg_dir / "scripts" / "start_flight.sh").exists()

    # Verify validator passes with zero errors
    validator = FlightPackageValidator(pkg_dir)
    is_valid, summary = validator.validate()
    assert is_valid is True, f"Validation errors: {summary.get('errors')}"
    assert summary["checked_artifacts_count"] > 100
    assert len(summary["errors"]) == 0

    # Ensure no dataset studio or training tools are in the package (Section 67)
    assert not (pkg_dir / "app" / "core" / "dataset").exists()
    assert not (pkg_dir / "app" / "core" / "training").exists()
