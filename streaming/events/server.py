# ==============================================================================
# ASTRA-EA Ground Telemetry Event Stream Server
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Lightweight HTTP Server-Sent Events (SSE) server for remote ground observability."""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

from streaming.events.publisher import EventPublisher
from streaming.events.schema import EventSeverity, EventType, GroundEvent
from streaming.protocol.base import IEventStreamServer

logger = logging.getLogger("event_server")


class _EventRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler supporting SSE streaming, replay, heartbeat, and evidence retrieval."""

    server: EventStreamServer

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard request logging."""
        pass

    def do_GET(self) -> None:
        """Route GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/events", "/stream"):
            self._handle_sse_stream()
        elif path == "/events/replay":
            self._handle_replay(parsed.query)
        elif path in ("/heartbeat", "/ping"):
            self._handle_heartbeat()
        elif path in ("/health", "/healthz"):
            self._handle_health()
        elif path.startswith("/evidence/"):
            self._handle_evidence(path[len("/evidence/") :])
        elif path == "/stats":
            self._handle_stats()
        elif path == "/":
            self._handle_root()
        else:
            self.send_error(404, "Endpoint Not Found")

    def _handle_root(self) -> None:
        """Root API metadata."""
        data = {
            "service": "astra_event_server",
            "version": "0.1.0",
            "endpoints": ["/events", "/events/replay?since={seq}", "/heartbeat", "/health", "/evidence/{id}", "/stats"],
            "current_sequence": self.server.publisher.current_sequence,
        }
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_heartbeat(self) -> None:
        """Instant heartbeat ping endpoint."""
        now_iso = datetime.now(timezone.utc).isoformat()
        data = {
            "status": "ONLINE",
            "service": "astra_telemetry",
            "timestamp": now_iso,
            "current_sequence": self.server.publisher.current_sequence,
            "uptime_seconds": round(time.time() - self.server.start_time, 2),
        }
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_health(self) -> None:
        """System health metrics."""
        body = json.dumps(self.server.get_health_metrics()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_stats(self) -> None:
        """Telemetry server metrics."""
        body = json.dumps(self.server.get_stats()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_replay(self, query_string: str) -> None:
        """Return missed events since sequence number."""
        query = parse_qs(query_string)
        since_str = query.get("since", ["0"])[0]
        try:
            since_seq = int(since_str)
        except ValueError:
            self.send_error(400, "Invalid 'since' sequence parameter")
            return

        events = self.server.publisher.get_events_since(since_seq)
        data = [e.model_dump() for e in events]
        body = json.dumps({"events": data, "count": len(data), "since_sequence": since_seq}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_evidence(self, evidence_id: str) -> None:
        """Safely fetch corroborating evidence bundle by ID (prevents path traversal)."""
        # Security sanitization: strip directory traversal characters
        safe_id = Path(evidence_id).name
        if not safe_id or ".." in evidence_id or "/" in evidence_id or "\\" in evidence_id:
            self.send_error(400, "Invalid evidence identifier")
            return

        evidence_dir = Path("storage/evidence")
        target_file = evidence_dir / f"{safe_id}.json"

        if not target_file.is_file():
            # Check for direct file match
            candidate = evidence_dir / safe_id
            if candidate.is_file():
                target_file = candidate
            else:
                self.send_error(404, f"Evidence bundle '{safe_id}' not found")
                return

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            self.send_error(500, f"Error reading evidence: {exc}")

    def _handle_sse_stream(self) -> None:
        """Stream continuous real-time Server-Sent Events (SSE)."""
        client_q: queue.Queue[GroundEvent] = queue.Queue(maxsize=100)
        self.server.publisher.register_listener(client_q)
        self.server.increment_client_count()

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Send initial greeting comment to flush headers
            self.wfile.write(b": astra-ea telemetry stream connected\n\n")
            self.wfile.flush()

            while self.server.is_running:
                try:
                    event = client_q.get(timeout=2.0)
                    sse_payload = event.to_sse().encode("utf-8")
                    self.wfile.write(sse_payload)
                    self.wfile.flush()
                except queue.Empty:
                    # Send keepalive ping comment to detect dead TCP sockets
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, socket.error):
            pass
        except Exception as exc:
            logger.debug("SSE client error: %s", exc)
        finally:
            self.server.publisher.unregister_listener(client_q)
            self.server.decrement_client_count()


class EventStreamServer(ThreadingHTTPServer, IEventStreamServer):
    """High-reliability HTTP SSE Event Stream Server for remote mission monitoring."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        heartbeat_interval_seconds: float = 2.0,
        publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval_seconds
        self.publisher = publisher or EventPublisher(buffer_capacity=500)

        self._running = False
        self._stop_event = threading.Event()
        self._server_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._active_clients: int = 0
        self._clients_lock = threading.Lock()
        self.start_time = time.time()
        self._health_metrics: Dict[str, Any] = {
            "perception": "ONLINE",
            "camera": "ONLINE",
            "assurance": "ONLINE",
            "storage": "ONLINE",
            "offline_mode": True,
        }

        self.allow_reuse_address = True
        super().__init__((self.host, self.port), _EventRequestHandler)

    def increment_client_count(self) -> None:
        with self._clients_lock:
            self._active_clients += 1
            logger.info("Ground event listener connected (Active: %d)", self._active_clients)

    def decrement_client_count(self) -> None:
        with self._clients_lock:
            self._active_clients = max(0, self._active_clients - 1)
            logger.info("Ground event listener disconnected (Active: %d)", self._active_clients)

    @property
    def active_client_count(self) -> int:
        with self._clients_lock:
            return self._active_clients

    def set_health_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update system health telemetry broadcasted to ground clients."""
        self._health_metrics.update(metrics)

    def get_health_metrics(self) -> Dict[str, Any]:
        """Return current health dictionary."""
        return {
            "status": "ONLINE" if self._running else "OFFLINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": self._health_metrics,
            "active_clients": self.active_client_count,
        }

    def start(self) -> None:
        """Start event server and background heartbeat generator."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self.start_time = time.time()

        self._server_thread = threading.Thread(
            target=self.serve_forever,
            daemon=True,
            name="astra_event_server",
        )
        self._server_thread.start()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="astra_heartbeat_emitter",
        )
        self._heartbeat_thread.start()

        logger.info("Event stream server started at http://%s:%d/events", self.host, self.port)

    def stop(self) -> None:
        """Stop server and heartbeat generator."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        try:
            self.shutdown()
            self.server_close()
        except Exception as exc:
            logger.warning("Error during event server shutdown: %s", exc)

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.0)
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)

        logger.info("Event stream server stopped.")

    def _heartbeat_loop(self) -> None:
        """Emit periodic HEARTBEAT telemetry events."""
        while self._running and not self._stop_event.is_set():
            interrupted = self._stop_event.wait(timeout=self.heartbeat_interval)
            if interrupted or not self._running:
                break
            # Emit heartbeat event
            self.publisher.create_event(
                event_type=EventType.HEARTBEAT,
                experiment_id="SYSTEM",
                run_id="HEARTBEAT",
                message="Onboard autonomous heartbeat",
                severity=EventSeverity.INFO,
                payload={"uptime": round(time.time() - self.start_time, 1)},
            )

    def publish_event(self, event: GroundEvent) -> bool:
        """Publish an event across the event server. Thread-safe and non-blocking."""
        if not self._running:
            return False
        return self.publisher.publish(event)

    @property
    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics."""
        return {
            "status": "ONLINE" if self._running else "OFFLINE",
            "host": self.host,
            "port": self.port,
            "endpoint_url": f"http://{self.host}:{self.port}/events",
            "active_clients": self.active_client_count,
            "current_sequence": self.publisher.current_sequence,
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "heartbeat_interval_seconds": self.heartbeat_interval,
        }
