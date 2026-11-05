# ==============================================================================
# ASTRA-EA Offline Voice Guidance Manager
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Local offline text-to-speech manager for astronaut voice assistance.

Air-gapped and self-contained using pyttsx3 with a priority worker thread,
deduplication cache, speech cooldowns, and headless fallback mode.
Delegates to core.voice subsystem.
"""

from __future__ import annotations

from typing import List

from core.assistance.interface import VoiceManager
from core.assistance.types import AssistantPriority
from core.common.logging import get_logger
from core.voice.interface import AudioPriority
from core.voice.manager import AudioQueueManager
from core.voice.offline_tts import OfflineTTSProvider
from core.voice.policies import AudioPolicy

logger = get_logger("voice_manager")


class LocalVoiceManager(VoiceManager):
    """Local offline TTS manager with queueing, cooldowns, and headless resilience."""

    def __init__(self, speech_rate: int = 165, volume: float = 0.9, headless: bool = False) -> None:
        self.speech_rate = speech_rate
        self.volume = volume
        self.headless = headless

        self._provider = OfflineTTSProvider(
            speech_rate=speech_rate,
            volume=volume,
            headless=headless,
        )
        self._policy = AudioPolicy(
            cooldowns={
                AudioPriority.CRITICAL: 2.0,
                AudioPriority.WARNING: 5.0,
                AudioPriority.GUIDANCE: 3.5,
                AudioPriority.INFO: 10.0,
            }
        )
        self._queue_manager = AudioQueueManager(
            provider=self._provider,
            policy=self._policy,
        )

    def speak(
        self,
        text: str,
        priority: AssistantPriority = AssistantPriority.GUIDANCE,
        cooldown: float = 3.5,
    ) -> bool:
        """Enqueue speech output subject to priority queueing and cooldowns."""
        # Map AssistantPriority to AudioPriority
        prio_map = {
            AssistantPriority.CRITICAL: AudioPriority.CRITICAL,
            AssistantPriority.WARNING: AudioPriority.WARNING,
            AssistantPriority.GUIDANCE: AudioPriority.GUIDANCE,
            AssistantPriority.INFO: AudioPriority.INFO,
        }
        audio_prio = prio_map.get(priority, AudioPriority.GUIDANCE)
        return self._queue_manager.speak(text, priority=audio_prio, custom_cooldown=cooldown)

    def stop(self) -> None:
        """Silence current speech and purge pending queue."""
        self._queue_manager.stop()

    @property
    def is_busy(self) -> bool:
        return self._queue_manager.is_busy

    @property
    def spoken_history(self) -> List[str]:
        return self._queue_manager.spoken_history

    def shutdown(self) -> None:
        self._queue_manager.shutdown()
