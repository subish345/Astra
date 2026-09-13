"""Automated Test Suite for ASTRA-EA Environmental & Hardware Qualification Program (Phase 17).

Validates:
- Qualification Baseline data models & Pydantic schemas (D17.15, D17.16)
- Qualification Telemetry multi-channel synchronization & uninstrumented null handling (D17.14)
- Nonconformance auditing and disposition tracking (D17.18)
- Dependency auditor & cryptographic supply-chain artifact verification (D17.13)
- Master Environmental Test Matrix 13-campaign integrity (D17.02)
- Qualification report generation & readiness verdict governance (D17.20, D17.22)
- Spacecraft power state transitions and brownout model (D17.09)
"""

import json
from pathlib import Path
import pytest

from core.qualification.dependencies import DependencyAuditor
from core.qualification.engine import QualificationEngine, QUALIFICATION_TESTS
from core.qualification.models import (
    EnvironmentalSensorData,
    NCRSeverity,
    NCRStatus,
    NonconformanceRecord,
    PowerState,
    QualificationItem,
    QualificationStatus,
    QualificationTelemetryFrame,
    SystemTelemetryData,
    TestProcedureSpec,
)
from core.qualification.telemetry import QualificationTelemetry


class TestEnvironmentalQualification:
    """Phase 17 Environmental & Hardware Qualification Test Suite."""

    @pytest.fixture
    def engine(self):
        return QualificationEngine()

    @pytest.fixture
    def auditor(self):
        return DependencyAuditor()

    def test_qualification_models_and_schemas(self):
        """Verify Pydantic models and JSON Schema definitions."""
        # 1. Qualification Item
        item = QualificationItem(
            id="ASTRA-EA-QB-001",
            hardware_version="REV-B",
            software_version="1.0.0-RC1",
            serial_number="ASTRA-SN-001",
            test_objective="Thermal Operational Stability",
            environment="Thermal (-10C to +50C)",
            acceptance_criteria=["Boot <= 5s", "Zero throttling"],
        )
        assert item.id == "ASTRA-EA-QB-001"
        assert len(item.acceptance_criteria) == 2

        # 2. Test Procedure Spec
        spec = TestProcedureSpec(
            test_id="QUAL-THM-001",
            objective="Thermal Operational Test",
            configuration="COTS Testbed",
            equipment=["Thermal Chamber"],
            setup=["Mount on baseplate"],
            instrumentation=["Thermocouple T1"],
            preconditions=["Power supply 28V"],
            procedure=["Step 1", "Step 2"],
            data_collection=["Log 1Hz telemetry"],
            acceptance_criteria=["Zero frame drop"],
            post_test_checks=["Functional test pass"],
            failure_handling=["Shutdown if >85C"],
            status=QualificationStatus.PLANNED,
        )
        assert spec.test_id == "QUAL-THM-001"
        assert spec.status == QualificationStatus.PLANNED

        # 3. Nonconformance Record
        ncr = NonconformanceRecord(
            ncr_id="NCR-TEST-001",
            qualification_build_id="ASTRA-EA-QB-001",
            test_id="QUAL-THM-001",
            requirement_id="ASTRA-ENV-004",
            severity=NCRSeverity.LOW,
            date_opened="2026-09-13T12:00:00Z",
            originator="QA Lead",
            failure_description="Transient temperature overshoot",
            root_cause="Heater pid tuning",
            corrective_action="Adjust PID gains",
            disposition="CORRECT_AND_RETEST",
            status=NCRStatus.CLOSED,
        )
        assert ncr.status == NCRStatus.CLOSED

        # 4. Verify JSON schema files on disk
        data_schema_path = Path("qualification/schemas/test_data_schema.json")
        proc_schema_path = Path("qualification/schemas/test_procedure_schema.json")
        assert data_schema_path.exists(), "test_data_schema.json must exist"
        assert proc_schema_path.exists(), "test_procedure_schema.json must exist"

        with open(data_schema_path, "r", encoding="utf-8") as f:
            ds = json.load(f)
            assert ds.get("title") == "QualificationTelemetryFrame"

        with open(proc_schema_path, "r", encoding="utf-8") as f:
            ps = json.load(f)
            assert ps.get("title") == "TestProcedureSpec"

    def test_telemetry_capture_and_null_handling(self):
        """Verify telemetry frame capture and strict null handling for uninstrumented channels (Section 38)."""
        telem = QualificationTelemetry(test_id="QUAL-TEST-FRAME")

        # Without external chamber provider, environmental sensor fields MUST remain null
        frame = telem.capture_frame()
        assert frame.test_id == "QUAL-TEST-FRAME"
        assert frame.qualification_id == "ASTRA-EA-QB-001"
        assert frame.environment.temperature_c is None
        assert frame.environment.pressure_torr is None
        assert frame.environment.acceleration_g_x is None
        assert frame.environment.radiation_dose_rad is None

        # System telemetry fields must be populated
        assert frame.system.ram_rss_mb is not None
        assert frame.system.ram_rss_mb > 0
        assert frame.system.power_state == PowerState.POWER_NOMINAL

        # Now test external environmental provider injection
        def mock_chamber_provider():
            return EnvironmentalSensorData(
                temperature_c=-10.5,
                pressure_torr=1e-5,
                bus_voltage_v=28.1,
                bus_current_a=0.62,
            )

        telem.set_environmental_provider(mock_chamber_provider)
        frame_inst = telem.capture_frame()
        assert frame_inst.environment.temperature_c == -10.5
        assert frame_inst.environment.pressure_torr == 1e-5
        assert frame_inst.environment.bus_voltage_v == 28.1

    def test_telemetry_clock_synchronization(self):
        """Verify time synchronization calibration with external chamber clock."""
        telem = QualificationTelemetry()
        master_chamber_clock = 1000.0
        telem.set_time_sync(master_chamber_clock)
        # Offset must be computed
        assert isinstance(telem.instrument_clock_offset_ms, float)

    def test_nonconformance_records_audit(self, engine):
        """Verify all tracked NCRs in qualification/nonconformance/ are audited."""
        ncr_audit = engine.audit_nonconformances()
        assert ncr_audit["total_ncrs"] >= 4
        assert ncr_audit["critical_open_ncrs"] == 0, "No open critical NCRs allowed in readiness baseline"
        assert ncr_audit["closed_ncrs"] >= 2
        assert ncr_audit["waived_ncrs"] >= 2

        # Check required fields in all records
        for r in ncr_audit["records"]:
            assert "ncr_id" in r
            assert "test_id" in r
            assert "severity" in r
            assert "status" in r
            assert "disposition" in r

    def test_dependency_auditor_and_artifacts(self, auditor):
        """Verify software dependencies and supply-chain SHA-256 provenance."""
        deps = auditor.audit_dependencies()
        assert deps["total_audited"] >= 9
        assert deps["approved_count"] >= 7
        assert deps["unapproved_count"] == 0

        # Verify cryptographic supply-chain artifacts
        art_report = auditor.verify_supply_chain_artifacts()
        assert art_report["total_artifacts"] == 4
        assert art_report["verified_count"] == 4, "All 4 frozen qualification artifacts must match SHA-256"

        for a in art_report["artifacts"]:
            assert a["status"] == "VERIFIED"
            assert len(a["sha256"]) == 64  # SHA-256 hex length

        # Verify ASCII report rendering
        ascii_rep = auditor.render_ascii_report()
        assert "ASTRA-EA DEPENDENCY AUDIT" in ascii_rep
        assert "CRITICAL SUPPLY-CHAIN ARTIFACT PROVENANCE" in ascii_rep

    def test_environmental_test_matrix_catalog(self, engine):
        """Verify all 13 environmental campaigns and strict PLANNED status rule."""
        tests = engine.list_qualification_tests()
        assert len(tests) == 13

        # ABSOLUTE RULE: Never mark environmental qualification tests as PASS
        # Ground tests remain PLANNED for future facilities
        for t in tests:
            assert t["status"] == QualificationStatus.PLANNED.value
            assert t["id"].startswith("QUAL-")
            assert len(t["facility"]) > 0
            assert len(t["acceptance"]) > 0

        test_ids = [t["id"] for t in tests]
        expected_ids = [
            "QUAL-THM-001",
            "QUAL-TVAC-001",
            "QUAL-VIB-001",
            "QUAL-VIB-002",
            "QUAL-SHK-001",
            "QUAL-EMC-001",
            "QUAL-EMC-002",
            "QUAL-EMC-003",
            "QUAL-RAD-001",
            "QUAL-RAD-002",
            "QUAL-PWR-001",
            "QUAL-REL-001",
            "QUAL-CAM-001",
        ]
        for eid in expected_ids:
            assert eid in test_ids

    def test_qualification_reports_generation(self, engine):
        """Verify generation of all 7 qualification reports + readiness.json."""
        reports = engine.generate_qualification_reports()
        assert len(reports) == 7

        rep_dir = Path("reports/qualification")
        expected_htmls = [
            "environmental_matrix.html",
            "qualification_status.html",
            "test_results.html",
            "nonconformances.html",
            "resource_report.html",
            "instrumentation.html",
            "final_qualification_readiness.html",
        ]
        for eh in expected_htmls:
            p = rep_dir / eh
            assert p.exists(), f"Report {eh} must exist"
            content = p.read_text(encoding="utf-8")
            assert "ASTRA-EA" in content or "Environmental" in content

        # Check readiness.json
        rj_path = rep_dir / "readiness.json"
        assert rj_path.exists()
        with open(rj_path, "r", encoding="utf-8") as f:
            rjd = json.load(f)
            assert rjd["readiness_verdict"] == "READY FOR FUTURE QUALIFICATION"
            assert rjd["qualification_build_id"] == "ASTRA-EA-QB-001"

    def test_power_state_transitions(self):
        """Verify power state transitions and brownout model."""
        telem = QualificationTelemetry()
        assert telem.current_power_state == PowerState.POWER_NOMINAL

        # Transition to WARNING
        telem.update_system_state(power_state=PowerState.POWER_WARNING)
        assert telem.current_power_state == PowerState.POWER_WARNING

        # Transition to CRITICAL
        telem.update_system_state(power_state=PowerState.POWER_CRITICAL)
        assert telem.current_power_state == PowerState.POWER_CRITICAL

        # Transition to LOSS
        telem.update_system_state(power_state=PowerState.POWER_LOSS)
        assert telem.current_power_state == PowerState.POWER_LOSS

        # Recovery back to NOMINAL
        telem.update_system_state(power_state=PowerState.POWER_RECOVERY)
        assert telem.current_power_state == PowerState.POWER_RECOVERY
