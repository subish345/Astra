# ==============================================================================
# ASTRA-EA Offline Text-to-Speech Provider
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Local, air-gapped speech synthesis provider wrapping pyttsx3 with headless fallback."""

from __future__ import annotations

import threading
from typing import Optional

from core.common.logging import get_logger
from core.voice.interface import AudioPriority, VoiceProvider

logger = get_logger("offline_tts")


class OfflineTTSProvider(VoiceProvider):
    """Local offline speech synthesizer using pyttsx3 with graceful headless fallback."""

    def __init__(
        self,
        speech_rate: int = 165,
        volume: float = 0.9,
        headless: bool = False,
    ) -> None:
        self.speech_rate = speech_rate
        self.volume = volume
        self.headless = headless

        self._engine = None
        self._is_busy = False
        self._lock = threading.Lock()

        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initialize the local pyttsx3 synthesis engine or switch to headless mock."""
        if self.headless:
            logger.info("OfflineTTSProvider initialized in headless mode.")
            return

        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.speech_rate)
            self._engine.setProperty("volume", self.volume)
            logger.info("OfflineTTSProvider loaded pyttsx3 engine successfully.")
        except Exception as e:
            logger.warning("Failed to initialize local pyttsx3 TTS (%s). Falling back to headless simulation.", e)
            self.headless = True
            self._engine = None

    def speak(self, text: str, priority: AudioPriority = AudioPriority.GUIDANCE) -> bool:
        """Synthesize spoken audio for the given text."""
        clean_text = text.strip()
        if not clean_text:
            return False

        logger.info("[AUDIO %s]: \"%s\"", priority.name, clean_text)

        with self._lock:
            self._is_busy = True

        try:
            if not self.headless and self._engine is not None:
                self._engine.say(clean_text)
                self._engine.runAndWait()
            return True
        except Exception as exc:
            logger.warning("OfflineTTS speech synthesis error (%s). Switching to headless mode.", exc)
            self.headless = True
            self._engine = None
            return False
        finally:
            with self._lock:
                self._is_busy = False

    def stop(self) -> None:
        """Interrupt active synthesis."""
        with self._lock:
            if self._engine is not None and not self.headless:
                try:
                    self._engine.stop()
                except Exception:
                    pass
            self._is_busy = False

    @property
    def is_busy(self) -> bool:
        """Return whether the synthesis provider is currently active."""
        with self._lock:
            return self._is_busy
