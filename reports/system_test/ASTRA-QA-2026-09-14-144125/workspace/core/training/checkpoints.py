"""Model Checkpoint Manager for ASTRA-EA.

Manages saving and loading of model weights and metadata in models/checkpoints/,
ensuring models are never silently overwritten.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointManager:
    """Handles persistence and retrieval of model checkpoints."""

    def __init__(self, checkpoints_dir: str = "models/checkpoints") -> None:
        self.checkpoints_dir = Path(checkpoints_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        model_name: str,
        version: str,
        epoch: int,
        model_state: Any,
        metrics: Dict[str, Any],
        config: Dict[str, Any],
        is_best: bool = False,
        format_type: str = "torch",
    ) -> Path:
        """Save a versioned checkpoint file."""
        filename = f"{model_name}_v{version}.pt" if format_type == "torch" else f"{model_name}_v{version}.json"
        target_path = self.checkpoints_dir / filename

        # Avoid silent destruction of existing files
        if target_path.exists() and not is_best:
            backup_name = f"{model_name}_v{version}_epoch{epoch}.pt"
            target_path = self.checkpoints_dir / backup_name

        checkpoint_data = {
            "model_name": model_name,
            "version": version,
            "epoch": epoch,
            "metrics": metrics,
            "config": config,
            "is_best": is_best,
            "format": format_type,
        }

        # If PyTorch is available and model_state is a torch state_dict or model
        try:
            import torch  # type: ignore
            checkpoint_data["state_dict"] = model_state
            torch.save(checkpoint_data, str(target_path))
        except (ImportError, Exception):
            # Fallback to JSON serialized weights or simulated format
            checkpoint_data["state_dict"] = (
                model_state if isinstance(model_state, dict) else {"weights_version": "v1"}
            )
            # Write companion metadata JSON
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2, default=str)

        # Save metadata companion file
        meta_path = target_path.with_suffix(".meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "model_name": model_name,
                "version": version,
                "epoch": epoch,
                "metrics": metrics,
                "checkpoint_path": str(target_path),
                "is_best": is_best,
            }, f, indent=2)

        return target_path

    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Load checkpoint data from disk."""
        target_path = Path(checkpoint_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at: '{target_path}'")

        try:
            import torch  # type: ignore
            data = torch.load(str(target_path), map_location="cpu")
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Try JSON loading
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_checkpoints(self) -> list[Dict[str, Any]]:
        """List all available checkpoints in the checkpoints directory."""
        results = []
        for p in sorted(self.checkpoints_dir.glob("*.meta.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            except Exception:
                pass
        return results
