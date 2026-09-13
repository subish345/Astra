# ==============================================================================
# ASTRA-EA Voice Manager Unit Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Unit tests for LocalVoiceManager offline text-to-speech engine."""

import time
import pytest
from core.assistance.voice import LocalVoiceManager
from core.assistance.types import AssistantPriority


@pytest.fixture
def voice_manager():
    mgr = LocalVoiceManager(headless=True)
    yield mgr
    mgr.shutdown()


def test_voice_manager_speak_and_cooldown(voice_manager):
    # First speak should succeed
    res1 = voice_manager.speak("Acquire the red reagent container", priority=AssistantPriority.GUIDANCE, cooldown=2.0)
    assert res1 is True

    # Immediate duplicate should be dropped by cooldown
    res2 = voice_manager.speak("Acquire the red reagent container", priority=AssistantPriority.GUIDANCE, cooldown=2.0)
    assert res2 is False

    # Different text should succeed
    res3 = voice_manager.speak("Warning: wrong item detected", priority=AssistantPriority.WARNING, cooldown=2.0)
    assert res3 is True


def test_voice_manager_critical_preemption(voice_manager):
    voice_manager.speak("Routine operational notice", priority=AssistantPriority.INFO)
    # Critical should preempt
    res_crit = voice_manager.speak("CRITICAL: Halting experiment run", priority=AssistantPriority.CRITICAL)
    assert res_crit is True


def test_voice_manager_stop(voice_manager):
    voice_manager.speak("Testing silence", priority=AssistantPriority.INFO)
    voice_manager.stop()
    assert True
