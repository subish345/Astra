# ==============================================================================
# ASTRA-EA Video Stream Server
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Local IP multipart MJPEG video streaming server with client backpressure isolation."""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Set
import numpy as np

from streaming.protocol.base import IVideoStreamServer
from streaming.video.config import StreamQuality, VideoStreamConfig
from streaming.video.encoder import StreamEncoder

logger = logging.getLogger("video_server")


class _MJPEGRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler providing MJPEG multipart video streaming and REST diagnostics."""

    server: VideoStreamServer  # Type hint for associated server

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard request logging to prevent console pollution."""
        pass

    def do_GET(self) -> None:
        """Route GET requests to video stream or diagnostics."""
        path = self.path.split("?")[0]

        if path in ("/video", "/stream"):
            self._handle_mjpeg_stream()
        elif path in ("/health", "/healthz"):
            self._handle_health()
        elif path == "/stats":
            self._handle_stats()
        elif path == "/":
            self._handle_index()
        else:
            self.send_error(404, "Endpoint Not Found")

    def _handle_index(self) -> None:
        """Serve an HTML browser preview page."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>ASTRA-EA Live Observation Stream</title>
    <style>
        body { background: #0b0f19; color: #e2e8f0; font-family: monospace; text-align: center; margin: 0; padding: 20px; }
        h1 { color: #38bdf8; font-size: 1.5rem; margin-bottom: 5px; }
        .badge { background: #0284c7; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; }
        .container { margin: 20px auto; max-width: 960px; background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; }
        img { max-width: 100%; height: auto; border: 1px solid #475569; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>ASTRA-EA Ground Video Stream</h1>
    <span class="badge">LOCAL IP OBSERVATION</span>
    <div class="container">
        <img src="/video" alt="ASTRA-EA Video Feed" />
    </div>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_health(self) -> None:
        """Return JSON health status."""
        data = {
            "status": "ONLINE" if self.server.is_running else "OFFLINE",
            "service": "astra_video_stream",
            "timestamp": time.time(),
            "port": self.server.config.port,
            "clients": self.server.active_client_count,
        }
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_stats(self) -> None:
        """Return JSON stream statistics."""
        body = json.dumps(self.server.get_stats()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_mjpeg_stream(self) -> None:
        """Transmit continuous multipart MJPEG frame stream with backpressure isolation."""
        if not self.server.can_accept_client():
            self.send_error(503, "Maximum client limit reached")
            return

        client_q: queue.Queue[bytes] = queue.Queue(maxsize=self.server.config.max_queue_size)
        self.server.register_client(client_q)

        try:
            self.send_response(200)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Connection", "close")
            self.end_headers()

            while self.server.is_running:
                try:
                    # Wait for next frame with timeout to detect server shutdown
                    jpeg_bytes = client_q.get(timeout=1.0)
                except queue.Empty:
                    continue

                header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg_bytes)).encode("ascii") + b"\r\n\r\n"
                )
                self.wfile.write(header)
                self.wfile.write(jpeg_bytes)
                self.wfile.write(b"\r\n")
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, socket.timeout, socket.error):
            # Client disconnected gracefully or abruptly
            pass
        except Exception as exc:
            logger.debug("Client stream ended: %s", exc)
        finally:
            self.server.unregister_client(client_q)


class VideoStreamServer(ThreadingHTTPServer, IVideoStreamServer):
    """High-reliability, non-blocking HTTP MJPEG streaming server."""

    def __init__(self, config: Optional[VideoStreamConfig] = None) -> None:
        self.config = config or VideoStreamConfig()
        self.encoder = StreamEncoder(self.config)

        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._clients_lock = threading.Lock()
        self._clients: Set[queue.Queue[bytes]] = set()

        # Telemetry metrics
        self.total_frames_submitted: int = 0
        self.total_frames_dropped: int = 0
        self.stream_fps: float = 0.0
        self._fps_frame_counter: int = 0
        self._last_fps_time: float = time.perf_counter()
        self.last_client_ip: Optional[str] = None

        # Allow instant socket reuse
        self.allow_reuse_address = True

        super().__init__((self.config.host, self.config.port), _MJPEGRequestHandler)

    def can_accept_client(self) -> bool:
        """Check if server has capacity for another client."""
        with self._clients_lock:
            return len(self._clients) < self.config.max_clients

    @property
    def active_client_count(self) -> int:
        """Current number of active ground observation clients."""
        with self._clients_lock:
            return len(self._clients)

    def register_client(self, client_q: queue.Queue[bytes]) -> None:
        """Register a new ground client queue."""
        with self._clients_lock:
            self._clients.add(client_q)
            logger.info("Ground client connected (Active: %d)", len(self._clients))

    def unregister_client(self, client_q: queue.Queue[bytes]) -> None:
        """Unregister a disconnected ground client."""
        with self._clients_lock:
            self._clients.discard(client_q)
            logger.info("Ground client disconnected (Active: %d)", len(self._clients))

    def start(self) -> None:
        """Start the video streaming HTTP server in a background thread."""
        if self._running:
            return

        self._running = True
        self._server_thread = threading.Thread(
            target=self.serve_forever,
            daemon=True,
            name="astra_video_server",
        )
        self._server_thread.start()
        logger.info("Video stream server started at http://%s:%d/video", self.config.host, self.config.port)

    def stop(self) -> None:
        """Shutdown video streaming server and clean up sockets."""
        if not self._running:
            return

        self._running = False
        try:
            self.shutdown()
            self.server_close()
        except Exception as exc:
            logger.warning("Error during video server shutdown: %s", exc)

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)

        with self._clients_lock:
            self._clients.clear()

        logger.info("Video stream server stopped.")

    def publish_frame(self, frame: np.ndarray) -> bool:
        """Non-blocking frame publication. Encodes frame and broadcasts to client queues.

        CRITICAL INVARIANT: This method NEVER blocks the caller (AI inference loop).
        If no clients are connected, returns immediately without encoding.
        """
        if not self._running or frame is None or frame.size == 0:
            return False

        self.total_frames_submitted += 1

        # Check if any clients are listening before spending CPU encoding
        with self._clients_lock:
            if not self._clients:
                return True  # No clients; drop silently without CPU penalty

            clients_snapshot = list(self._clients)

        # Encode frame
        jpeg_bytes = self.encoder.encode(frame)
        if jpeg_bytes is None:
            self.total_frames_dropped += 1
            return False

        # Broadcast to each client queue using non-blocking put with drop-oldest policy
        for client_q in clients_snapshot:
            try:
                # If queue is full, discard the old frame to keep stream real-time
                if client_q.full():
                    try:
                        client_q.get_nowait()
                        self.total_frames_dropped += 1
                    except queue.Empty:
                        pass
                client_q.put_nowait(jpeg_bytes)
            except Exception:
                self.total_frames_dropped += 1

        # Update FPS calculation
        self._fps_frame_counter += 1
        now = time.perf_counter()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self.stream_fps = round(self._fps_frame_counter / elapsed, 1)
            self._fps_frame_counter = 0
            self._last_fps_time = now

        return True

    @property
    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics."""
        encoder_stats = self.encoder.get_stats()
        return {
            "status": "ONLINE" if self._running else "OFFLINE",
            "host": self.config.host,
            "port": self.config.port,
            "stream_url": f"http://{self.config.host}:{self.config.port}/video",
            "active_clients": self.active_client_count,
            "max_clients": self.config.max_clients,
            "stream_fps": self.stream_fps,
            "target_fps": self.config.fps,
            "width": self.config.width,
            "height": self.config.height,
            "quality": self.config.quality.value,
            "jpeg_quality": self.config.jpeg_quality,
            "total_submitted": self.total_frames_submitted,
            "total_dropped": self.total_frames_dropped,
            "encoder": encoder_stats,
        }
