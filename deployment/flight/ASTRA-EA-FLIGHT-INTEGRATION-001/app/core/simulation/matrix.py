"""Batch Simulation Matrix Runner for ASTRA-EA.

Executes parameterized fault test matrices across scenarios, evaluating overall
pipeline resilience, fault detection reliability, and zero-crash compliance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.perception.detection.interface import ObjectDetector
from core.simulation.engine import SimulationEngine, SimulationRunResult
from core.simulation.reporter import SimulationReporter
from core.simulation.scenario import SimulationScenario


class SimulationMatrixRunner:
    """Orchestrates batch scenario execution and resilience aggregation."""

    def __init__(
        self,
        config_path: str = "configs/system.yaml",
        reports_dir: str = "storage/reports/simulation",
        detector_override: Optional[ObjectDetector] = None,
    ) -> None:
        self.config_path = config_path
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.detector_override = detector_override
        self.engine = SimulationEngine(
            config_path=config_path,
            detector_override=detector_override,
        )
        self.reporter = SimulationReporter(output_dir=str(self.reports_dir))

    def run_matrix(
        self,
        scenarios: List[SimulationScenario],
        matrix_name: str = "Full Simulation Fault Matrix",
        max_frames_per_scenario: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute all scenarios in the matrix sequentially."""
        print("=" * 70)
        print(f"ASTRA-EA SIMULATION MATRIX: {matrix_name}")
        print(f"Total Scenarios to Execute: {len(scenarios)}")
        print("=" * 70)

        results: List[SimulationRunResult] = []
        for idx, scen in enumerate(scenarios, start=1):
            print(f"[{idx:02d}/{len(scenarios):02d}] Simulating: {scen.name} ({scen.scenario_id})...")
            res = self.engine.run_scenario(
                scenario=scen,
                max_frames=max_frames_per_scenario,
                realtime_pacing=False,
            )
            results.append(res)
            print(
                f"       Verdict: {res.evaluation_verdict} | "
                f"Resilience: {res.resilience_score:.1f}% | "
                f"Frames: {res.frames_processed} | "
                f"Decisions: V:{res.verified_count} U:{res.uncertain_count} D:{res.deviation_count}"
            )

        report = self.reporter.generate_matrix_report(
            results=results,
            matrix_name=matrix_name,
        )

        print("-" * 70)
        print(f"Simulation Matrix Complete.")
        print(f"Pass Rate: {report['passed_scenarios']}/{report['total_scenarios']} ({report['pass_rate']}%)")
        print(f"Average Resilience: {report['average_resilience_score']:.1f}%")
        print(f"HTML Report: {self.reports_dir}/simulation_matrix_report.html")
        print("=" * 70)

        return report

    def run_matrix_config(
        self,
        config_path: str = "configs/simulations/full_matrix.yaml",
        max_frames: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Load scenarios specified in a matrix configuration file and run."""
        c_path = Path(config_path)
        if not c_path.exists():
            raise FileNotFoundError(f"Matrix config file not found: '{config_path}'")

        import yaml
        with open(c_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        scenario_paths = data.get("scenarios", [])
        matrix_name = data.get("name", c_path.stem)
        cfg_max_frames = data.get("max_frames_per_scenario", None)
        effective_max_frames = max_frames if max_frames is not None else cfg_max_frames

        scenarios = [SimulationScenario.load_yaml(p) for p in scenario_paths]
        return self.run_matrix(
            scenarios=scenarios,
            matrix_name=matrix_name,
            max_frames_per_scenario=effective_max_frames,
        )

    def run_directory(
        self,
        scenarios_dir: str = "configs/simulations",
        max_frames: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Load all YAML scenarios in directory and execute matrix."""
        s_dir = Path(scenarios_dir)
        yaml_files = sorted(list(s_dir.glob("*.yaml")))
        # Exclude matrix index configs
        yaml_files = [f for f in yaml_files if f.name not in {"full_matrix.yaml"}]

        if not yaml_files:
            raise FileNotFoundError(f"No scenario YAML files found in '{scenarios_dir}'.")

        scenarios = [SimulationScenario.load_yaml(f) for f in yaml_files]
        return self.run_matrix(
            scenarios=scenarios,
            matrix_name=f"Batch Suite ({s_dir.name})",
            max_frames_per_scenario=max_frames,
        )

