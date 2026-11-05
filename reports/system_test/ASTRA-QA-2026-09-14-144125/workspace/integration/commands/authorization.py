"""Flight Command Authorization for ASTRA-EA (Phase 18).

In accordance with Section 24:
Uses AuthorizationPolicy for future spacecraft ground/vehicle integration.
Defaults to LOCAL_OPERATOR authority without artificial complexity.
"""

from __future__ import annotations

import enum
from typing import Set

from integration.commands.schema import CommandType, FlightCommand


class AuthorizationRole(str, enum.Enum):
    LOCAL_OPERATOR = "LOCAL_OPERATOR"
    FLIGHT_CONTROLLER_TBD = "FLIGHT_CONTROLLER_TBD"
    GROUND_STATION_TBD = "GROUND_STATION_TBD"
    AUTOMATED_SCHEDULE_TBD = "AUTOMATED_SCHEDULE_TBD"


class AuthorizationPolicy:
    """Evaluates whether an originator has authority to issue a command."""

    def __init__(self, default_role: AuthorizationRole = AuthorizationRole.LOCAL_OPERATOR) -> None:
        self.default_role = default_role
        # Permitted command sets per role
        self._role_permissions: dict[AuthorizationRole, Set[CommandType]] = {
            AuthorizationRole.LOCAL_OPERATOR: set(CommandType),
            AuthorizationRole.FLIGHT_CONTROLLER_TBD: set(CommandType),
            AuthorizationRole.GROUND_STATION_TBD: set(CommandType),
            AuthorizationRole.AUTOMATED_SCHEDULE_TBD: {
                CommandType.REQUEST_STATUS,
                CommandType.START_EXPERIMENT,
                CommandType.STOP_EXPERIMENT,
            },
        }

    def is_authorized(self, command: FlightCommand) -> bool:
        """Check if command originator is permitted to execute target command."""
        role = AuthorizationRole.LOCAL_OPERATOR
        try:
            role = AuthorizationRole(command.originator)
        except Exception:
            pass

        perms = self._role_permissions.get(role, set())
        return command.command_type in perms
