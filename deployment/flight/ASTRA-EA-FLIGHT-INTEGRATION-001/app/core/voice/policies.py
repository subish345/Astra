# ==============================================================================
# ASTRA-EA Audio Policies & Deduplication
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Audio policy, cooldown timing, deduplication, and preemption management."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from core.voice.interface import AudioPriority


@dataclass
class AudioPolicy:
    """Configurable audio cooldowns and deduplication rules."""

    cooldowns: Dict[AudioPriority, float] = field(
        default_factory=lambda: {
            AudioPriority.CRITICAL: 2.0,
            AudioPriority.WARNING: 5.0,
            AudioPriority.GUIDANCE: 3.5,
            AudioPriority.INFO: 10.0,
        }
    )
    preempt_on_critical: bool = True
    deduplicate: bool = True

    def get_cooldown(self, priority: AudioPriority) -> float:
        """Retrieve cooldown interval in seconds for the given priority level."""
        return self.cooldowns.get(priority, 3.5)


class AudioDeduplicator:
    """Tracks message timestamps to prevent repetitive spoken utterances."""

    def __init__(self, policy: Optional[AudioPolicy] = None) -> None:
        self.policy = policy or AudioPolicy()
        self._last_spoken_times: Dict[str, float] = {}

    def should_speak(self, text: str, priority: AudioPriority, current_time: Optional[float] = None) -> bool:
        """Evaluate whether a message is allowed to be spoken under active cooldown policies.

        Returns True if utterance is permitted, False if currently throttled.
        """
        if not self.policy.deduplicate:
            return True

        now = current_time if current_time is not None else time.time()
        normalized_key = text.strip().lower()
        if not normalized_key:
            return False

        last_time = self._last_spoken_times.get(normalized_key, 0.0)
        cooldown = self.policy.get_cooldown(priority)

        if (now - last_time) < cooldown:
            return False

        self._last_spoken_times[normalized_key] = now
        return True

    def record_spoken(self, text: str, timestamp: Optional[float] = None) -> None:
        """Manually update the last spoken timestamp for a message."""
        now = timestamp if timestamp is not None else time.time()
        self._last_spoken_times[text.strip().lower()] = now

    def clear(self) -> None:
        """Reset deduplication history."""
        self._last_spoken_times.clear()
