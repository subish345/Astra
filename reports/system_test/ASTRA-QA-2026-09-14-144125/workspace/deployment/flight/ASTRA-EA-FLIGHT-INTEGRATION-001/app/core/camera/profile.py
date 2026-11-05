# ==============================================================================
# ASTRA-EA Camera Profiles & Viewpoint Management
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Camera profile definitions and viewpoint registry for viewpoint-invariant experiment assurance."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml

from core.common.config import get_project_root
from core.common.logging import get_logger

logger = get_logger("camera_profile")


class CameraViewpoint(str, Enum):
    VIEW_LEFT = "VIEW_LEFT"
    VIEW_RIGHT = "VIEW_RIGHT"
    VIEW_CENTER = "VIEW_CENTER"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: str) -> CameraViewpoint:
        val_norm = val.strip().upper().replace("-", "_")
        if val_norm in ("VIEW_LEFT", "LEFT", "VIEW_A"):
            return cls.VIEW_LEFT
        if val_norm in ("VIEW_RIGHT", "RIGHT", "VIEW_B"):
            return cls.VIEW_RIGHT
        if val_norm in ("VIEW_CENTER", "CENTER", "FRONT"):
            return cls.VIEW_CENTER
        try:
            return cls(val_norm)
        except ValueError:
            return cls.UNKNOWN


class CameraProfile(BaseModel):
    id: str = Field(default="VIEW_LEFT")
    name: str = Field(default="Standard Camera View")
    description: str = Field(default="")
    horizontal_bias: str = Field(default="CENTER")  # "LEFT", "RIGHT", "CENTER"
    nominal_distance_m: float = Field(default=1.2, ge=0.1)
    elevation_deg: float = Field(default=15.0)
    azimuth_deg: float = Field(default=0.0)
    field_of_view_deg: float = Field(default=78.0, ge=10.0, le=180.0)

    @property
    def viewpoint(self) -> CameraViewpoint:
        return CameraViewpoint.from_str(self.id)


class CameraProfileRegistry:
    """Registry maintaining available camera viewpoint profiles."""

    def __init__(self, config_path: Optional[str | Path] = None) -> None:
        self._profiles: Dict[str, CameraProfile] = {}
        self._config_path = config_path or (get_project_root() / "configs" / "cameras" / "profiles.yaml")
        self._load_profiles()

    def _load_profiles(self) -> None:
        path = Path(self._config_path)
        if not path.is_absolute():
            path = get_project_root() / path

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                raw_profiles = data.get("profiles", {})
                for key, pdata in raw_profiles.items():
                    profile = CameraProfile(**pdata)
                    self._profiles[profile.id.upper()] = profile
                    self._profiles[key.upper()] = profile
            except Exception as e:
                logger.warning("Failed to parse camera profiles from %s: %s. Using defaults.", path, e)

        # Ensure minimal default profiles exist
        if "VIEW_LEFT" not in self._profiles:
            self._profiles["VIEW_LEFT"] = CameraProfile(
                id="VIEW_LEFT",
                name="Left-Side Perspective",
                description="Camera positioned toward the front-left observation quadrant",
                horizontal_bias="LEFT",
                azimuth_deg=-35.0,
            )
        if "VIEW_RIGHT" not in self._profiles:
            self._profiles["VIEW_RIGHT"] = CameraProfile(
                id="VIEW_RIGHT",
                name="Right-Side Perspective",
                description="Camera positioned toward the front-right observation quadrant",
                horizontal_bias="RIGHT",
                azimuth_deg=35.0,
            )
        if "VIEW_CENTER" not in self._profiles:
            self._profiles["VIEW_CENTER"] = CameraProfile(
                id="VIEW_CENTER",
                name="Center Front Perspective",
                description="Camera positioned orthogonally in front of the experiment workstation",
                horizontal_bias="CENTER",
                azimuth_deg=0.0,
            )

    def get_profile(self, profile_id_or_name: str) -> CameraProfile:
        normalized = profile_id_or_name.strip().upper().replace("-", "_")
        if normalized in ("VIEW_A", "LEFT"):
            normalized = "VIEW_LEFT"
        elif normalized in ("VIEW_B", "RIGHT"):
            normalized = "VIEW_RIGHT"
        elif normalized in ("CENTER", "FRONT"):
            normalized = "VIEW_CENTER"

        if normalized in self._profiles:
            return self._profiles[normalized]
        # Try matching lower or substring
        for k, prof in self._profiles.items():
            if k == normalized or prof.id == normalized:
                return prof
        return self._profiles["VIEW_LEFT"]

    def list_profiles(self) -> List[CameraProfile]:
        # Return unique by id
        seen = set()
        result = []
        for p in self._profiles.values():
            if p.id not in seen:
                seen.add(p.id)
                result.append(p)
        return result


# Global default registry instance
_default_registry: Optional[CameraProfileRegistry] = None


def get_camera_profile_registry() -> CameraProfileRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CameraProfileRegistry()
    return _default_registry


def get_camera_profile(profile_id: str) -> CameraProfile:
    return get_camera_profile_registry().get_profile(profile_id)
