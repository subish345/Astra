"""Flight Runtime Mode and Security Policy Enforcement for ASTRA-EA (Phase 18).

In accordance with Section 9, 31, 39, 67 & 68:
Enforces strict separation between DEVELOPMENT, DEMO, VALIDATION, and FLIGHT_INTEGRATION modes.
In FLIGHT_INTEGRATION mode:
- Disables developer shortcuts and debug menus
- Locks runtime configuration as immutable
- Blocks test/synthetic data injection into production evidence paths
- Prohibits arbitrary runtime model swapping
- Ensures training and dataset studio tools cannot be invoked
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class RuntimeMode(str, enum.Enum):
    DEVELOPMENT = "DEVELOPMENT"
    DEMO = "DEMO"
    VALIDATION = "VALIDATION"
    FLIGHT_INTEGRATION = "FLIGHT_INTEGRATION"


class SecurityPolicyViolation(Exception):
    """Raised when an operation violates the active runtime security policy."""
    pass


@dataclass
class RuntimePolicy:
    mode: RuntimeMode
    allow_debug_controls: bool
    allow_config_mutation: bool
    allow_synthetic_injection: bool
    allow_model_swapping: bool
    allow_dataset_studio: bool
    require_checksum_audit: bool


def get_policy_for_mode(mode: RuntimeMode) -> RuntimePolicy:
    """Return security policy settings for target execution mode."""
    if mode == RuntimeMode.FLIGHT_INTEGRATION:
        return RuntimePolicy(
            mode=mode,
            allow_debug_controls=False,
            allow_config_mutation=False,
            allow_synthetic_injection=False,
            allow_model_swapping=False,
            allow_dataset_studio=False,
            require_checksum_audit=True,
        )
    elif mode == RuntimeMode.VALIDATION:
        return RuntimePolicy(
            mode=mode,
            allow_debug_controls=True,
            allow_config_mutation=False,
            allow_synthetic_injection=True,
            allow_model_swapping=False,
            allow_dataset_studio=False,
            require_checksum_audit=True,
        )
    elif mode == RuntimeMode.DEMO:
        return RuntimePolicy(
            mode=mode,
            allow_debug_controls=False,
            allow_config_mutation=False,
            allow_synthetic_injection=False,
            allow_model_swapping=False,
            allow_dataset_studio=False,
            require_checksum_audit=False,
        )
    else:  # DEVELOPMENT
        return RuntimePolicy(
            mode=mode,
            allow_debug_controls=True,
            allow_config_mutation=True,
            allow_synthetic_injection=True,
            allow_model_swapping=True,
            allow_dataset_studio=True,
            require_checksum_audit=False,
        )


class FlightSecurityGuard:
    """Enforces runtime boundaries in flight integration builds."""

    def __init__(self, mode: Optional[RuntimeMode] = None) -> None:
        # Default can be configured via environment variable
        env_mode = os.environ.get("ASTRA_RUNTIME_MODE", "FLIGHT_INTEGRATION")
        try:
            self.mode = mode or RuntimeMode(env_mode)
        except ValueError:
            self.mode = RuntimeMode.FLIGHT_INTEGRATION
        self.policy = get_policy_for_mode(self.mode)

    def assert_debug_allowed(self) -> None:
        if not self.policy.allow_debug_controls:
            raise SecurityPolicyViolation("Debug controls are disabled in FLIGHT_INTEGRATION mode.")

    def assert_config_mutation_allowed(self) -> None:
        if not self.policy.allow_config_mutation:
            raise SecurityPolicyViolation("Configuration is locked and immutable in FLIGHT_INTEGRATION mode.")

    def assert_synthetic_injection_allowed(self) -> None:
        if not self.policy.allow_synthetic_injection:
            raise SecurityPolicyViolation("Synthetic data injection is prohibited in FLIGHT_INTEGRATION mode.")

    def assert_model_swapping_allowed(self) -> None:
        if not self.policy.allow_model_swapping:
            raise SecurityPolicyViolation("Model swapping is prohibited in FLIGHT_INTEGRATION mode.")
