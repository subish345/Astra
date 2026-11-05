# ==============================================================================
# ASTRA-EA Audio UX Interface
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Interface specifications and priority definitions for the Audio UX subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Optional


@unique
class AudioPriority(int, Enum):
    """Audio urgency levels determining queue order and preemption behavior."""

    CRITICAL = 1    # Procedure deviation, emergency alert - preempts pending speech
    WARNING = 2     # Wrong object, caution, impending timeout
    GUIDANCE = 3    # Next step instruction, recovery direction
    INFO = 4        # Nominal completion, system status confirmation

    @property
    def label(self) -> str:
        return self.name


class VoiceProvider(ABC):
    """Abstract interface for local offline speech synthesis providers."""

    @abstractmethod
    def speak(self, text: str, priority: AudioPriority = AudioPriority.GUIDANCE) -> bool:
        """Synthesize speech utterance. Returns True if successfully handled."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Immediately silence active and pending speech synthesis."""
        pass

    @property
    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if speech synthesis is actively outputting audio."""
        pass
