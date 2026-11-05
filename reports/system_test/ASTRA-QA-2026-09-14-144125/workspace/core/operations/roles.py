"""Operator Roles and Authority Model for ASTRA-EA (Phase 19, D19.03, D19.04).

Defines role responsibilities, access control policies, and command authority rules
governing both onboard and ground operations.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Set, Tuple


class OperatorRole(str, Enum):
    """Operations roles participating in mission lifecycle (Section 5)."""
    ASTRONAUT_OPERATOR = "ASTRONAUT_OPERATOR"
    MISSION_OPERATOR = "MISSION_OPERATOR"
    GROUND_MONITOR = "GROUND_MONITOR"
    SYSTEM_ENGINEER = "SYSTEM_ENGINEER"
    DATA_REVIEWER = "DATA_REVIEWER"
    MAINTAINER = "MAINTAINER"
    LOCAL_OPERATOR = "LOCAL_OPERATOR"  # Consolidated role for standalone demonstration


class Permission(str, Enum):
    """Action permissions governed by the authority model (Section 7)."""
    START_EXPERIMENT = "START_EXPERIMENT"
    PAUSE_EXPERIMENT = "PAUSE_EXPERIMENT"
    RESUME_EXPERIMENT = "RESUME_EXPERIMENT"
    STOP_EXPERIMENT = "STOP_EXPERIMENT"
    REQUEST_STATUS = "REQUEST_STATUS"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    REQUEST_REPORT = "REQUEST_REPORT"
    ACKNOWLEDGE_ALERT = "ACKNOWLEDGE_ALERT"
    VIEW_LOGS = "VIEW_LOGS"
    EXPORT_REPORT = "EXPORT_REPORT"
    ENTER_MAINTENANCE = "ENTER_MAINTENANCE"
    RUN_DIAGNOSTICS = "RUN_DIAGNOSTICS"


class AuthorityModel:
    """Manages role-based command permissions and enforces operational boundaries."""

    # Role permission mappings
    ROLE_PERMISSIONS: Dict[OperatorRole, Set[Permission]] = {
        OperatorRole.ASTRONAUT_OPERATOR: {
            Permission.START_EXPERIMENT,
            Permission.PAUSE_EXPERIMENT,
            Permission.RESUME_EXPERIMENT,
            Permission.STOP_EXPERIMENT,
            Permission.REQUEST_STATUS,
            Permission.ACKNOWLEDGE_ALERT,
        },
        OperatorRole.MISSION_OPERATOR: {
            Permission.START_EXPERIMENT,
            Permission.PAUSE_EXPERIMENT,
            Permission.RESUME_EXPERIMENT,
            Permission.STOP_EXPERIMENT,
            Permission.REQUEST_STATUS,
            Permission.REQUEST_EVIDENCE,
            Permission.REQUEST_REPORT,
            Permission.ACKNOWLEDGE_ALERT,
            Permission.VIEW_LOGS,
            Permission.EXPORT_REPORT,
        },
        OperatorRole.GROUND_MONITOR: {
            Permission.REQUEST_STATUS,
            Permission.REQUEST_EVIDENCE,
            Permission.REQUEST_REPORT,
            Permission.ACKNOWLEDGE_ALERT,
            Permission.VIEW_LOGS,
        },
        OperatorRole.SYSTEM_ENGINEER: {
            Permission.REQUEST_STATUS,
            Permission.REQUEST_EVIDENCE,
            Permission.REQUEST_REPORT,
            Permission.ACKNOWLEDGE_ALERT,
            Permission.VIEW_LOGS,
            Permission.EXPORT_REPORT,
            Permission.ENTER_MAINTENANCE,
            Permission.RUN_DIAGNOSTICS,
        },
        OperatorRole.DATA_REVIEWER: {
            Permission.REQUEST_STATUS,
            Permission.REQUEST_EVIDENCE,
            Permission.REQUEST_REPORT,
            Permission.VIEW_LOGS,
            Permission.EXPORT_REPORT,
        },
        OperatorRole.MAINTAINER: {
            Permission.REQUEST_STATUS,
            Permission.VIEW_LOGS,
            Permission.ENTER_MAINTENANCE,
            Permission.RUN_DIAGNOSTICS,
        },
        # Consolidated demonstration role possessing full operational authority
        OperatorRole.LOCAL_OPERATOR: {
            Permission.START_EXPERIMENT,
            Permission.PAUSE_EXPERIMENT,
            Permission.RESUME_EXPERIMENT,
            Permission.STOP_EXPERIMENT,
            Permission.REQUEST_STATUS,
            Permission.REQUEST_EVIDENCE,
            Permission.REQUEST_REPORT,
            Permission.ACKNOWLEDGE_ALERT,
            Permission.VIEW_LOGS,
            Permission.EXPORT_REPORT,
            Permission.ENTER_MAINTENANCE,
            Permission.RUN_DIAGNOSTICS,
        },
    }

    def __init__(self, active_role: OperatorRole = OperatorRole.LOCAL_OPERATOR) -> None:
        self.active_role = active_role

    def set_role(self, role: OperatorRole) -> None:
        """Switch active operational role."""
        self.active_role = role

    def check_authority(self, permission: Permission, role: OperatorRole | None = None) -> Tuple[bool, str]:
        """Check if role possesses the given permission (Section 7)."""
        target_role = role or self.active_role
        perms = self.ROLE_PERMISSIONS.get(target_role, set())
        if permission in perms:
            return True, f"Role '{target_role.value}' is authorized for '{permission.value}'."
        return False, f"Role '{target_role.value}' is NOT authorized for '{permission.value}'."

    def require_authority(self, permission: Permission, role: OperatorRole | None = None) -> None:
        """Enforce authority, raising PermissionError if unauthorized."""
        authorized, reason = self.check_authority(permission, role)
        if not authorized:
            raise PermissionError(f"Operational Authority Violation: {reason}")
