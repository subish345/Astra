"""Deployment Profile Loader for ASTRA-EA.

Loads and validates layered deployment configurations from configs/deployment/:
- development.yaml
- balanced.yaml
- realtime.yaml
- low_resource.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from core.common.logging import get_logger

logger = get_logger("OPTIMIZATION")

DEPLOYMENT_DIR = Path("configs/deployment")


class DeploymentProfileManager:
    """Manages discovery and loading of edge deployment profiles."""

    @classmethod
    def list_profiles(cls) -> List[str]:
        """Return available deployment profile names."""
        if not DEPLOYMENT_DIR.exists():
            return []
        return sorted([p.stem for p in DEPLOYMENT_DIR.glob("*.yaml")])

    @classmethod
    def load_profile(cls, profile_name: str = "balanced") -> Dict[str, Any]:
        """Load profile configuration dictionary by name."""
        stem = profile_name.replace(".yaml", "")
        file_path = DEPLOYMENT_DIR / f"{stem}.yaml"
        if not file_path.exists():
            logger.warning("Profile '%s' not found, defaulting to 'balanced.yaml'.", file_path)
            file_path = DEPLOYMENT_DIR / "balanced.yaml"

        with open(file_path, "r") as f:
            data = yaml.safe_load(f) or {}

        data["_file_path"] = str(file_path)
        return data
