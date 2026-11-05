# ==============================================================================
# ASTRA-EA Audio Architecture Unit Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Unit tests for core.voice subsystem: provider, manager, policies, and fallback."""

import time
import pytest

from core.voice.interface import AudioPriority, VoiceProvider
from core.voice.manager import AudioQueueManager
from core.voice.offline_tts import OfflineTTSProvider
from core.voice.policies import AudioDeduplicator, AudioPolicy


class MockVoiceProvider(VoiceProvider):
    """Test double recording spoken utterances without sound hardware."""

    def __init__(self) -> None:
        self.spoken: list[tuple[str, AudioPriority]] = []
        self._busy = False

    def speak(self, text: str, priority: AudioPriority = AudioPriority.GUIDANCE) -> bool:
        self._busy = True
        self.spoken.append((text, priority))
        self._busy = False
        return True

    def stop(self) -> None:
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy


class FailingVoiceProvider(VoiceProvider):
    """Test double simulating a hardware audio crash."""

    def speak(self, text: str, priority: AudioPriority = AudioPriority.GUIDANCE) -> bool:
        raise RuntimeError("Audio device disconnected / ALSA error")

    def stop(self) -> None:
        pass

    @property
    def is_busy(self) -> bool:
        return False


def test_audio_deduplicator_cooldown():
    policy = AudioPolicy(cooldowns={AudioPriority.WARNING: 3.0, AudioPriority.CRITICAL: 1.0})
    dedup = AudioDeduplicator(policy)

    t0 = 1000.0
    # First utterance allowed
    assert dedup.should_speak("Check container alignment", AudioPriority.WARNING, current_time=t0) is True

    # Immediate duplicate blocked
    assert dedup.should_speak("Check container alignment", AudioPriority.WARNING, current_time=t0 + 1.0) is False

    # After cooldown expires, allowed
    assert dedup.should_speak("Check container alignment", AudioPriority.WARNING, current_time=t0 + 3.1) is True


def test_audio_queue_manager_priorities_and_preemption():
    provider = MockVoiceProvider()
    policy = AudioPolicy(
        cooldowns={
            AudioPriority.CRITICAL: 0.05,
            AudioPriority.WARNING: 0.05,
            AudioPriority.GUIDANCE: 0.05,
            AudioPriority.INFO: 0.05,
        }
    )
    spoken_events: list[str] = []

    def on_spoken_cb(text: str, prio: AudioPriority):
        spoken_events.append(text)

    manager = AudioQueueManager(provider=provider, policy=policy, on_spoken=on_spoken_cb)

    # Queue first message and wait for it to finish speaking
    manager.speak("Procedure initialized", priority=AudioPriority.INFO)
    time.sleep(0.1)

    # Queue an utterance, then immediately preempt with CRITICAL
    manager.speak("Telemetry nominal", priority=AudioPriority.INFO)
    manager.speak("CRITICAL: Container pressure drop detected", priority=AudioPriority.CRITICAL)

    time.sleep(0.2)
    manager.shutdown()

    # The first message spoke
    assert any("Procedure initialized" in text for text, _ in provider.spoken)
    # The critical message spoke
    assert any("CRITICAL" in text for text, _ in provider.spoken)
    # The callback received events
    assert len(spoken_events) >= 2


def test_audio_manager_failing_provider_resilience():
    """Verify that a failing voice provider does not crash the queue manager or caller."""
    failing = FailingVoiceProvider()
    manager = AudioQueueManager(provider=failing)

    # Must not raise an exception
    res = manager.speak("Testing system resilience", priority=AudioPriority.GUIDANCE)
    assert res is True

    time.sleep(0.2)
    manager.shutdown()


def test_offline_tts_provider_headless_mode():
    provider = OfflineTTSProvider(headless=True)
    assert provider.headless is True
    res = provider.speak("Simulated offline voice guidance", priority=AudioPriority.GUIDANCE)
    assert res is True
    assert provider.is_busy is False
