# ==============================================================================
# ASTRA-EA Ground Telemetry Event Client
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Background SSE event stream client with automatic reconnection and replay reconciliation."""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from streaming.events.schema import GroundEvent
from streaming.protocol.base import IStreamClient

logger = logging.getLogger("event_client")


class EventStreamClient(IStreamClient):
    """Client connecting to remote SSE event stream, receiving live events and requesting replay."""

    def __init__(
        self,
        events_url: str = "http://127.0.0.1:8765/events",
        on_event_callback: Optional[Callable[[GroundEvent, float], None]] = None,
        on_status_callback: Optional[Callable[[bool, str], None]] = None,
        reconnect_interval_seconds: float = 2.0,
    ) -> None:
        self.events_url = events_url
        self.on_event = on_event_callback
        self.on_status = on_status_callback
        self.reconnect_interval = reconnect_interval_seconds

        self._running = False
        self._connected = False
        self._thread: Optional[threading.Thread] = None

        # Sequence and reconciliation tracking
        self.last_sequence_received: int = 0
        self.total_events_received: int = 0
        self.reconnect_count: int = 0
        self.last_heartbeat_time: float = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Start background connection thread."""
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._client_loop,
            daemon=True,
            name="astra_event_client",
        )
        self._thread.start()
        return True

    def disconnect(self) -> None:
        """Stop client."""
        self._running = False
        self._connected = False
        if self.on_status:
            try:
                self.on_status(False, "DISCONNECTED")
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Event stream client stopped.")

    def _get_base_url(self) -> str:
        parsed = urllib.parse.urlparse(self.events_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _fetch_missed_events(self) -> None:
        """Query replay endpoint to fetch missed events during network disconnection."""
        if self.last_sequence_received <= 0:
            return

        base_url = self._get_base_url()
        replay_url = f"{base_url}/events/replay?since={self.last_sequence_received}"
        try:
            req = urllib.request.Request(replay_url, headers={"User-Agent": "ASTRA-EA-GroundMonitor/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    missed = payload.get("events", [])
                    if missed:
                        logger.info("Replaying %d missed events since seq #%d", len(missed), self.last_sequence_received)
                        for item in missed:
                            event = GroundEvent(**item)
                            self._process_event(event, is_replay=True)
        except Exception as exc:
            logger.debug("Event replay fetch error: %s", exc)

    def _client_loop(self) -> None:
        """Continuous SSE reading loop with auto-reconnect."""
        while self._running:
            try:
                logger.info("Connecting to event stream at %s...", self.events_url)
                req = urllib.request.Request(
                    self.events_url,
                    headers={
                        "User-Agent": "ASTRA-EA-GroundMonitor/1.0",
                        "Accept": "text/event-stream",
                    },
                )
                with urllib.request.urlopen(req, timeout=10.0) as response:
                    self._connected = True
                    self.last_heartbeat_time = time.time()
                    if self.on_status:
                        try:
                            self.on_status(True, "CONNECTED")
                        except Exception:
                            pass
                    logger.info("Connected to event stream.")

                    # Fetch any missed events immediately upon reconnection
                    self._fetch_missed_events()

                    # Stream line by line
                    event_id = None
                    event_type = None
                    data_lines: List[str] = []

                    for raw_line in response:
                        if not self._running:
                            break
                        line = raw_line.decode("utf-8").strip("\r\n")

                        # Empty line signals dispatch of SSE message
                        if not line:
                            if data_lines:
                                full_data = "\n".join(data_lines)
                                try:
                                    event = GroundEvent.from_json_str(full_data)
                                    self._process_event(event)
                                except Exception as parse_err:
                                    logger.debug("Failed to parse event data: %s", parse_err)
                                data_lines = []
                                event_id = None
                                event_type = None
                            continue

                        # Comment / ping
                        if line.startswith(":"):
                            self.last_heartbeat_time = time.time()
                            continue

                        if line.startswith("id:"):
                            event_id = line[len("id:") :].strip()
                        elif line.startswith("event:"):
                            event_type = line[len("event:") :].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[len("data:") :].strip())

            except Exception as exc:
                self._connected = False
                if self.on_status:
                    try:
                        self.on_status(False, f"LINK_LOST ({type(exc).__name__})")
                    except Exception:
                        pass
                logger.debug("Event stream disconnected: %s. Reconnecting in %.1fs...", exc, self.reconnect_interval)
                self.reconnect_count += 1

            if self._running:
                time.sleep(self.reconnect_interval)

    def _process_event(self, event: GroundEvent, is_replay: bool = False) -> None:
        """Dispatch event to callback and compute network transit latency."""
        now = time.time()
        self.last_heartbeat_time = now
        self.total_events_received += 1

        if event.sequence_num > self.last_sequence_received:
            self.last_sequence_received = event.sequence_num

        # Compute latency: difference between client receipt and onboard timestamp
        latency_ms = 0.0
        try:
            # Parse ISO 8601 onboard timestamp
            onboard_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            client_dt = datetime.now(timezone.utc)
            delta = (client_dt - onboard_dt).total_seconds() * 1000.0
            latency_ms = max(0.0, round(delta, 2))
        except Exception:
            pass

        if self.on_event:
            try:
                self.on_event(event, latency_ms)
            except Exception as exc:
                logger.error("Error in event callback: %s", exc)
