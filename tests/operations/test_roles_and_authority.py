"""Automated Tests for Operations Roles and Authority Model (Phase 19, D19.03, D19.04)."""

import pytest

from core.operations.roles import AuthorityModel, OperatorRole, Permission


def test_operator_roles_and_permissions():
    """Verify role permission mappings and authority enforcement."""
    auth = AuthorityModel(active_role=OperatorRole.ASTRONAUT_OPERATOR)

    # Astronaut can start and acknowledge
    ok, _ = auth.check_authority(Permission.START_EXPERIMENT)
    assert ok is True
    ok, _ = auth.check_authority(Permission.ACKNOWLEDGE_ALERT)
    assert ok is True

    # Astronaut cannot export report or enter maintenance
    ok, _ = auth.check_authority(Permission.EXPORT_REPORT)
    assert ok is False
    ok, _ = auth.check_authority(Permission.ENTER_MAINTENANCE)
    assert ok is False

    with pytest.raises(PermissionError):
        auth.require_authority(Permission.ENTER_MAINTENANCE)


def test_ground_monitor_read_only_restriction():
    """Verify Ground Monitor has observation authority but cannot mutate onboard execution."""
    auth = AuthorityModel(active_role=OperatorRole.GROUND_MONITOR)

    # Allowed observation
    assert auth.check_authority(Permission.REQUEST_STATUS)[0] is True
    assert auth.check_authority(Permission.REQUEST_EVIDENCE)[0] is True
    assert auth.check_authority(Permission.ACKNOWLEDGE_ALERT)[0] is True

    # Forbidden direct control (Section 23)
    assert auth.check_authority(Permission.START_EXPERIMENT)[0] is False
    assert auth.check_authority(Permission.STOP_EXPERIMENT)[0] is False
    assert auth.check_authority(Permission.ENTER_MAINTENANCE)[0] is False


def test_local_operator_consolidated_authority():
    """Verify consolidated LOCAL_OPERATOR demonstration role possesses all necessary permissions."""
    auth = AuthorityModel(active_role=OperatorRole.LOCAL_OPERATOR)
    for perm in Permission:
        assert auth.check_authority(perm)[0] is True
