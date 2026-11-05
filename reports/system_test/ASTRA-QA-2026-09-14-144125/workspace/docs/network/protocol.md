# ASTRA-EA Network Wire Protocol Specification

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Classification:** Phase 9 Network Wire Protocol Specification

---

## 1. Port Allocation

| Port | Protocol | Service | Description |
| :--- | :--- | :--- | :--- |
| **8554** | TCP / HTTP | Video Stream Server | Multipart MJPEG real-time video stream & video stats |
| **8765** | TCP / HTTP | Event Stream Server | Server-Sent Events (SSE), replay API, and evidence queries |

---

## 2. Video Stream Endpoints (`:8554`)

### 2.1 `GET /video` (or `GET /stream`)
- **Content-Type:** `multipart/x-mixed-replace; boundary=frame`
- **Cache-Control:** `no-cache, no-store, must-revalidate`
- **Wire Format:**
  ```http
  --frame\r\n
  Content-Type: image/jpeg\r\n
  Content-Length: <length_in_bytes>\r\n\r\n
  <raw_jpeg_bytes>\r\n
  ```

### 2.2 `GET /health`
- **Content-Type:** `application/json`
- **Response Schema:**
  ```json
  {
    "status": "ONLINE",
    "service": "astra_video_stream",
    "timestamp": 1789295600.12,
    "port": 8554,
    "clients": 1
  }
  ```

### 2.3 `GET /stats`
- **Content-Type:** `application/json`
- **Response Schema:**
  ```json
  {
    "status": "ONLINE",
    "host": "127.0.0.1",
    "port": 8554,
    "active_clients": 1,
    "stream_fps": 15.0,
    "target_fps": 15,
    "width": 1280,
    "height": 720,
    "total_submitted": 450,
    "total_dropped": 0,
    "encoder": {
      "avg_encode_ms": 3.02,
      "last_frame_kb": 540.6
    }
  }
  ```

---

## 3. Telemetry Event Endpoints (`:8765`)

### 3.1 `GET /events` (SSE Stream)
- **Content-Type:** `text/event-stream; charset=utf-8`
- **Cache-Control:** `no-cache, no-transform`
- **Wire Format:**
  ```text
  id: 1
  event: STEP_VERIFIED
  data: {"event_id":"EVT_000001_A1B2","sequence_num":1,"timestamp":"2026-09-13T12:00:00Z","event_type":"STEP_VERIFIED","step_id":"STEP_01","status":"VERIFIED","severity":"INFO","message":"Step STEP_01 Verified"}

  : ping
  ```

### 3.2 `GET /events/replay?since={seq}`
- **Query Parameters:** `since` (integer sequence number)
- **Response Schema:**
  ```json
  {
    "events": [ ... ],
    "count": 2,
    "since_sequence": 12
  }
  ```

### 3.3 `GET /heartbeat`
- **Response Schema:**
  ```json
  {
    "status": "ONLINE",
    "service": "astra_telemetry",
    "timestamp": "2026-09-13T12:00:02Z",
    "current_sequence": 45,
    "uptime_seconds": 120.4
  }
  ```

### 3.4 `GET /evidence/{evidence_id}`
- **Response Schema:** JSON representation of the corroborating multimodal `EvidenceBundle`.
- **Error Codes:** `400 Bad Request` (path traversal detected), `404 Not Found` (bundle does not exist).
