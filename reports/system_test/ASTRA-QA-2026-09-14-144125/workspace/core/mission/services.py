"""Service Registry and Subsystem Lifecycle Interfaces for ASTRA-EA.

Provides clean dependency injection, service discovery, and unified lifecycle management
(initialize -> start -> stop -> health) across all Onboard Core subsystems.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from core.common.logging import get_logger

logger = get_logger("SERVICES")


class ServiceStatus(str, Enum):
    """Operational status of a registered mission service."""
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class Service(ABC):
    """Abstract mission service lifecycle interface."""

    def __init__(self, service_name: str, is_critical: bool = True) -> None:
        self.service_name = service_name
        self.is_critical = is_critical
        self._status: ServiceStatus = ServiceStatus.UNINITIALIZED
        self._last_error: Optional[str] = None
        self._last_health_check: float = 0.0

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @abstractmethod
    def initialize(self) -> bool:
        """Allocate resources, validate configurations, and verify readiness."""
        ...

    @abstractmethod
    def start(self) -> bool:
        """Commence active processing/service loops."""
        ...

    @abstractmethod
    def stop(self) -> bool:
        """Gracefully release hardware and flush pending queues."""
        ...

    def health(self) -> Dict[str, Any]:
        """Query detailed operational health metrics."""
        return {
            "service": self.service_name,
            "status": self._status.value,
            "is_critical": self.is_critical,
            "last_error": self._last_error,
            "timestamp": time.time(),
        }

    def set_status(self, status: ServiceStatus, error: Optional[str] = None) -> None:
        """Update internal status and record error if applicable."""
        self._status = status
        if error:
            self._last_error = error


T = TypeVar("T", bound=Service)


class ServiceRegistry:
    """Central registry governing service lifecycles and dependency access."""

    def __init__(self) -> None:
        self._services: Dict[str, Service] = {}
        self._lock = threading.RLock()
        # Ordered list ensuring deterministic initialization and teardown sequence
        self._registration_order: List[str] = []

    def register(self, service: Service) -> None:
        """Register a subsystem service."""
        with self._lock:
            name = service.service_name
            self._services[name] = service
            if name not in self._registration_order:
                self._registration_order.append(name)
            logger.debug("Registered service: %s (Critical: %s)", name, service.is_critical)

    def get(self, service_name: str) -> Optional[Service]:
        """Retrieve registered service by identifier."""
        with self._lock:
            return self._services.get(service_name)

    def get_typed(self, service_type: Type[T]) -> Optional[T]:
        """Retrieve registered service by type."""
        with self._lock:
            for s in self._services.values():
                if isinstance(s, service_type):
                    return s
            return None

    def initialize_all(self) -> Dict[str, bool]:
        """Initialize all registered services in order."""
        results: Dict[str, bool] = {}
        with self._lock:
            for name in self._registration_order:
                svc = self._services[name]
                try:
                    logger.info("Initializing service: %s...", name)
                    ok = svc.initialize()
                    results[name] = ok
                    svc.set_status(ServiceStatus.INITIALIZED if ok else ServiceStatus.FAILED)
                except Exception as exc:
                    logger.error("Failed to initialize service %s: %s", name, exc)
                    svc.set_status(ServiceStatus.FAILED, str(exc))
                    results[name] = False
        return results

    def start_all(self) -> Dict[str, bool]:
        """Start all initialized services in order."""
        results: Dict[str, bool] = {}
        with self._lock:
            for name in self._registration_order:
                svc = self._services[name]
                if svc.status == ServiceStatus.INITIALIZED:
                    try:
                        logger.info("Starting service: %s...", name)
                        ok = svc.start()
                        results[name] = ok
                        svc.set_status(ServiceStatus.RUNNING if ok else ServiceStatus.FAILED)
                    except Exception as exc:
                        logger.error("Failed to start service %s: %s", name, exc)
                        svc.set_status(ServiceStatus.FAILED, str(exc))
                        results[name] = False
                else:
                    results[name] = False
        return results

    def stop_all(self) -> Dict[str, bool]:
        """Stop all services in reverse registration order."""
        results: Dict[str, bool] = {}
        with self._lock:
            for name in reversed(self._registration_order):
                svc = self._services[name]
                try:
                    logger.info("Stopping service: %s...", name)
                    ok = svc.stop()
                    results[name] = ok
                    svc.set_status(ServiceStatus.STOPPED)
                except Exception as exc:
                    logger.error("Error stopping service %s: %s", name, exc)
                    results[name] = False
        return results

    def aggregate_health(self) -> Dict[str, Any]:
        """Collect health metrics across all registered services."""
        with self._lock:
            services_health = {name: svc.health() for name, svc in self._services.items()}
            critical_failed = any(
                svc.is_critical and svc.status == ServiceStatus.FAILED
                for svc in self._services.values()
            )
            degraded = any(
                svc.status in (ServiceStatus.DEGRADED, ServiceStatus.FAILED)
                for svc in self._services.values()
            )

            if critical_failed:
                overall = "FAILED"
            elif degraded:
                overall = "DEGRADED"
            else:
                overall = "NORMAL"

            return {
                "overall_status": overall,
                "total_services": len(self._services),
                "services": services_health,
            }
