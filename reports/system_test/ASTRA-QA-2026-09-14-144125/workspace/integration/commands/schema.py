"""Flight Command Schemas for ASTRA-EA (Phase 18).

In accordance with Section 21, 22 & 23:
Defines flight command types, status codes, and execution responses.
Strictly prohibits direct spacecraft actuator commands unless specified.
"""

from __future__ import annotations

import enum
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


class CommandType(str, enum.Enum):
    """Permitted flight payload command set (Section 21)."""
    REQUEST_STATUS = "REQUEST_STATUS"
    START_EXPERIMENT = "START_EXPERIMENT"
    STOP_EXPERIMENT = "STOP_EXPERIMENT"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    REQUEST_REPORT = "REQUEST_REPORT"


class CommandStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


@dataclass
class FlightCommand:
    """Standardized flight uplink command packet (Section 21 & 22)."""
    command_id: str
    command_type: CommandType
    sequence_number: int
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    originator: str = "LOCAL_OPERATOR"
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["command_type"] = self.command_type.value
        return d


@dataclass
class CommandResponse:
    """Execution response returned to commanding authority."""
    command_id: str
    status: CommandStatus
    message: str = "OK"
    error_code: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    execution_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "message": self.message,
            "error_code": self.error_code,
            "payload": self.payload,
            "execution_duration_ms": self.execution_duration_ms,
        }
