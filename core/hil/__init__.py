"""Hardware-in-the-Loop Architecture for ASTRA-EA (Phase 18)."""

from core.hil.flight_runner import HILFlightIntegrationRunner, HILScenarioResult
from core.hil.hil_platform import HILPlatform, HILPlatformConfig

__all__ = [
    "HILPlatform",
    "HILPlatformConfig",
    "HILFlightIntegrationRunner",
    "HILScenarioResult",
]
