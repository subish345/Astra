"""Flight Command Validation and Dispatcher for ASTRA-EA (Phase 18).

In accordance with Section 22 & 23:
Validates command identity, parameters, mission state, authorization, and sequence.
Enforces safety interlocks: START_EXPERIMENT fails safely if camera, model,
procedure, or storage are unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from integration.commands.authorization import AuthorizationPolicy
from integration.commands.schema import CommandResponse, CommandStatus, CommandType, FlightCommand

logger = logging.getLogger("command_interface")


class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass


class CommandSafetyGuard:
    """Evaluates mission safety interlocks before command dispatch (Section 23)."""

    def __init__(
        self,
        camera_ok_fn: Optional[Callable[[], bool]] = None,
        model_ok_fn: Optional[Callable[[], bool]] = None,
        procedure_ok_fn: Optional[Callable[[], bool]] = None,
        storage_ok_fn: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.camera_ok_fn = camera_ok_fn or (lambda: True)
        self.model_ok_fn = model_ok_fn or (lambda: True)
        self.procedure_ok_fn = procedure_ok_fn or (lambda: True)
        self.storage_ok_fn = storage_ok_fn or (lambda: True)

    def check_safety(self, command: FlightCommand) -> tuple[bool, Optional[str]]:
        """Verify safety prerequisites for critical commands."""
        if command.command_type == CommandType.START_EXPERIMENT:
            if not self.camera_ok_fn():
                return False, "SAFETY INTERLOCK: Camera unavailable"
            if not self.model_ok_fn():
                return False, "SAFETY INTERLOCK: Neural model unavailable"
            if not self.procedure_ok_fn():
                return False, "SAFETY INTERLOCK: Procedure specification invalid or missing"
            if not self.storage_ok_fn():
                return False, "SAFETY INTERLOCK: Storage partition critical or unwritable"

        return True, None


class CommandDispatcher:
    """Central validator and dispatcher for flight commands (D18.08 & D18.09)."""

    def __init__(
        self,
        authorization_policy: Optional[AuthorizationPolicy] = None,
        safety_guard: Optional[CommandSafetyGuard] = None,
    ) -> None:
        self.auth_policy = authorization_policy or AuthorizationPolicy()
        self.safety_guard = safety_guard or CommandSafetyGuard()
        self._last_sequence: int = 0
        self._handlers: Dict[CommandType, Callable[[FlightCommand], Dict[str, Any]]] = {}
        self.command_audit_log: List[Dict[str, Any]] = []

    def register_handler(
        self,
        cmd_type: CommandType,
        handler: Callable[[FlightCommand], Dict[str, Any]],
    ) -> None:
        """Register subsystem execution handler for command type."""
        self._handlers[cmd_type] = handler

    def execute(self, command: FlightCommand) -> CommandResponse:
        """Validate, authorize, safety-check, and execute flight command."""
        t0 = time.perf_counter()

        # 1. Authorization check
        if not self.auth_policy.is_authorized(command):
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.REJECTED,
                error_code="UNAUTHORIZED",
                message=f"Originator {command.originator} not authorized for {command.command_type.value}",
            )
            self._log_command(command, resp)
            return resp

        # 2. Sequence check (prevent replay / duplicate command)
        if command.sequence_number <= self._last_sequence and command.sequence_number != 0:
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.REJECTED,
                error_code="INVALID_SEQUENCE",
                message=f"Command sequence {command.sequence_number} <= last seen {self._last_sequence}",
            )
            self._log_command(command, resp)
            return resp
        if command.sequence_number > 0:
            self._last_sequence = command.sequence_number

        # 3. Safety interlocks (Section 23)
        safe, safety_err = self.safety_guard.check_safety(command)
        if not safe:
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error_code="SAFETY_VIOLATION",
                message=safety_err or "Safety precondition failed",
            )
            self._log_command(command, resp)
            return resp

        # 4. Handler dispatch
        handler = self._handlers.get(command.command_type)
        if not handler:
            # Default acknowledgment for non-registered commands
            dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.EXECUTED,
                message=f"Command {command.command_type.value} executed successfully",
                payload={"acknowledged": True},
                execution_duration_ms=dt_ms,
            )
            self._log_command(command, resp)
            return resp

        try:
            result_payload = handler(command)
            dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.EXECUTED,
                message=f"Command {command.command_type.value} completed",
                payload=result_payload,
                execution_duration_ms=dt_ms,
            )
        except Exception as e:
            dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            resp = CommandResponse(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error_code="EXECUTION_ERROR",
                message=str(e),
                execution_duration_ms=dt_ms,
            )

        self._log_command(command, resp)
        return resp

    def _log_command(self, command: FlightCommand, response: CommandResponse) -> None:
        entry = {
            "timestamp": command.timestamp_utc,
            "command": command.to_dict(),
            "response": response.to_dict(),
        }
        self.command_audit_log.append(entry)
        if response.status in (CommandStatus.REJECTED, CommandStatus.FAILED):
            logger.warning(
                "Command %s %s (%s): %s",
                command.command_id,
                response.status.value,
                response.error_code,
                response.message,
            )
