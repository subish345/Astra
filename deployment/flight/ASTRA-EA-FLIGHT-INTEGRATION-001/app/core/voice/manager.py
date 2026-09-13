# ==============================================================================
# ASTRA-EA Audio Queue & Priority Manager
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Thread-safe audio queue manager with priority preemption, deduplication, and cooldowns."""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, List, Optional

from core.common.logging import get_logger
from core.voice.interface import AudioPriority, VoiceProvider
from core.voice.offline_tts import OfflineTTSProvider
from core.voice.policies import AudioDeduplicator, AudioPolicy

logger = get_logger("audio_manager")


class AudioQueueManager:
    """Manages audio speech queue, enforcing priority ordering, preemption, and cooldowns."""

    def __init__(
        self,
        provider: Optional[VoiceProvider] = None,
        policy: Optional[AudioPolicy] = None,
        on_spoken: Optional[Callable[[str, AudioPriority], None]] = None,
    ) -> None:
        self.provider = provider or OfflineTTSProvider()
        self.policy = policy or AudioPolicy()
        self.deduplicator = AudioDeduplicator(self.policy)
        self.on_spoken = on_spoken

        # PriorityQueue elements: (priority_int, timestamp, text, priority_enum)
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._spoken_history: List[str] = []
        self._stop_requested = False

        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    @property
    def is_enabled(self) -> bool:
        """Return whether audio manager and provider are active."""
        return not self._stop_requested and self.provider is not None

    def _worker_loop(self) -> None:
        """Background loop consuming items from the priority queue."""
        while not self._stop_requested:
            try:
                prio_int, item_ts, text, priority_enum = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                success = self.provider.speak(text, priority=priority_enum)
                if success:
                    with self._lock:
                        self._spoken_history.append(text)
                    if self.on_spoken:
                        try:
                            self.on_spoken(text, priority_enum)
                        except Exception as e:
                            logger.error("Error in on_spoken audio callback: %s", e)
            except Exception as exc:
                logger.error("Error synthesizing audio utterance: %s", exc)
            finally:
                self._queue.task_done()

    def speak(
        self,
        text: str,
        priority: AudioPriority = AudioPriority.GUIDANCE,
        custom_cooldown: Optional[float] = None,
    ) -> bool:
        """Enqueue speech utterance subject to deduplication and priority rules.

        Returns True if enqueued, False if rejected by cooldown or empty.
        """
        clean_text = text.strip()
        if not clean_text:
            return False

        # Apply deduplication policy
        if custom_cooldown is not None:
            # Temporary override
            original_cd = self.policy.cooldowns.get(priority, 3.5)
            self.policy.cooldowns[priority] = custom_cooldown
            allowed = self.deduplicator.should_speak(clean_text, priority)
            self.policy.cooldowns[priority] = original_cd
        else:
            allowed = self.deduplicator.should_speak(clean_text, priority)

        if not allowed:
            logger.debug("Speech suppressed by cooldown for priority %s: '%s'", priority.name, clean_text)
            return False

        now = time.time()

        # If CRITICAL, preempt queue and stop active speech if enabled
        if priority == AudioPriority.CRITICAL and self.policy.preempt_on_critical:
            self._purge_queue()
            self.provider.stop()

        self._queue.put((int(priority.value), now, clean_text, priority))
        return True

    def _purge_queue(self) -> None:
        """Drain all pending items from queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except (queue.Empty, ValueError):
                break

    def stop(self) -> None:
        """Immediately silence active output and purge pending queue."""
        self._purge_queue()
        self.provider.stop()

    def shutdown(self) -> None:
        """Terminate worker thread cleanly."""
        self._stop_requested = True
        self.stop()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    @property
    def is_busy(self) -> bool:
        """Return True if speaking or pending utterances exist."""
        return self.provider.is_busy or not self._queue.empty()

    @property
    def spoken_history(self) -> List[str]:
        """Return copy of spoken message history."""
        with self._lock:
            return list(self._spoken_history)
