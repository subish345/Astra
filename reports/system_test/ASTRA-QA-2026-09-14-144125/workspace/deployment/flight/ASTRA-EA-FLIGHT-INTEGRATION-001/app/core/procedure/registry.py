"""Experiment Registry for ASTRA-EA.

Discovers, validates, registers, and resolves experiment procedures from configs/experiments/:
- Lists available experiments and versions
- Validates procedure schema and step transition topologies
- Resolves target objects, required tools, and evidence verification rules
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.common.logging import get_logger
from core.procedure.schema import ExperimentProcedure
from core.procedure.validator import validate_experiment_definition

logger = get_logger("EXPERIMENT_REGISTRY")


class ExperimentRegistry:
    """Central registry discovering and validating experiment procedure definitions."""

    def __init__(self, search_dir: str = "configs/experiments") -> None:
        self.search_dir = Path(search_dir)
        self._cache: Dict[str, ExperimentProcedure] = {}
        self._file_map: Dict[str, Path] = {}
        self.refresh()

    def refresh(self) -> int:
        """Scan directory and index all valid YAML experiment files."""
        self._cache.clear()
        self._file_map.clear()

        count = 0
        search_dirs = [self.search_dir]
        project_experiments = Path("configs/experiments")
        if project_experiments.exists() and project_experiments.resolve() != self.search_dir.resolve():
            search_dirs.append(project_experiments)

        for s_dir in search_dirs:
            if not s_dir.exists():
                continue
            for yaml_path in s_dir.glob("*.yaml"):
                try:
                    with open(yaml_path, "r") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and "experiment" in data:
                        exp_data = data["experiment"]
                        exp_id = exp_data.get("id")
                        if exp_id and exp_id not in self._file_map:
                            self._file_map[exp_id] = yaml_path
                            # Also map filename stem
                            self._file_map[yaml_path.stem] = yaml_path
                            count += 1
                except Exception as e:
                    logger.warning("Skipping unparsable procedure file %s: %s", yaml_path, e)

        return count

    def list_experiments(self) -> List[Dict[str, Any]]:
        """Return summary of all registered experiments."""
        experiments = []
        for exp_id, path in self._file_map.items():
            if exp_id != path.stem:  # Avoid duplicates from stem mapping
                proc = self.get_procedure(exp_id)
                if proc:
                    experiments.append({
                        "experiment_id": proc.experiment.id,
                        "name": proc.experiment.name,
                        "version": proc.experiment.version,
                        "total_steps": len(proc.steps),
                        "file_path": str(path),
                        "objects": [obj.id for obj in proc.objects] if proc.objects else [],
                    })
        return sorted(experiments, key=lambda x: x["experiment_id"])

    def get_procedure(self, experiment_id_or_path: str) -> Optional[ExperimentProcedure]:
        """Load and return validated ExperimentProcedure by ID or relative path."""
        # 1. Direct path check
        path = Path(experiment_id_or_path)
        if not path.is_file() and experiment_id_or_path in self._file_map:
            path = self._file_map[experiment_id_or_path]

        if not path.is_file():
            # Try searching directory with .yaml suffix
            candidate = self.search_dir / f"{experiment_id_or_path}.yaml"
            if candidate.is_file():
                path = candidate
            else:
                return None

        cache_key = str(path.resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            proc = ExperimentProcedure(**data)
            self._cache[cache_key] = proc
            return proc
        except Exception as e:
            logger.error("Failed to load experiment procedure from %s: %s", path, e)
            return None

    def validate_procedure(self, experiment_id_or_path: str) -> Dict[str, Any]:
        """Validate procedure structure and semantic consistency."""
        proc = self.get_procedure(experiment_id_or_path)
        if not proc:
            return {
                "status": "FAIL",
                "valid": False,
                "errors": [f"Experiment not found: {experiment_id_or_path}"],
            }

        errors = validate_experiment_definition(proc)
        return {
            "status": "PASS" if len(errors) == 0 else "FAIL",
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": [],
            "experiment_id": proc.experiment.id,
            "total_steps": len(proc.steps),
        }
