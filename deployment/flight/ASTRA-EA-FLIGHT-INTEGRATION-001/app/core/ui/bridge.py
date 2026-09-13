# ==============================================================================
# ASTRA-EA Backend-to-UI Event Bridge
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Thread-safe event bridge connecting background AI inference workers to the Qt UI."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import QObject, Signal


class BackendEventBridge(QObject):
    """Qt Signal bridge emitting typed events from backend threads to the Qt UI thread.

    Ensures that Qt GUI widgets are ONLY manipulated on the main Qt application thread.
    """

    # Video frame and perception overlays: (numpy_image, PerceptionState)
    sig_frame_ready = Signal(object, object)

    # Procedure progress update: (ProcedureProgressState)
    sig_step_progress = Signal(object)

    # Assurance decision update: (AssuranceDecision, Optional[ExperimentStep])
    sig_assurance_decision = Signal(object, object)

    # Corroborating evidence bundle: (EvidenceBundle)
    sig_evidence_bundle = Signal(object)

    # Procedural deviation detected: (AssuranceDecision, ExperimentStep)
    sig_deviation = Signal(object, object)

    # Closed-loop recovery update: (RecoveryContext)
    sig_recovery = Signal(object)

    # Spoken audio notification: (text, priority_name)
    sig_voice = Signal(str, str)

    # Subsystem health heartbeat: (dict of metrics and states)
    sig_health = Signal(dict)

    # Chronological mission timeline event: (event_type, title, description, severity)
    sig_timeline_event = Signal(str, str, str, str)

    # Overall mission session status changed: (status_str)
    sig_session_status = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
