# ASTRA-EA Network & Telemetry Security Specification

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Classification:** Phase 9 Network Security, Access Control, and Threat Mitigation

---

## 1. Security Architecture & Threat Model

In flight operations, the ASTRA-EA Onboard core and Ground Monitor communicate across an isolated spacecraft LAN or umbilical tether. Despite the physical/air-gapped network boundary, Phase 9 enforces multi-layer defensive programming to guarantee that network degradation, buggy clients, or adversarial injections cannot compromise onboard flight assurance.

```text
GROUND MONITOR (Untrusted Client Context)
       │
       ▼ [TCP HTTP / SSE]
┌─────────────────────────────────────────────────────────────┐
│ ONBOARD BOUNDARY DEFENSES                                  │
│                                                             │
│ 1. Bind Address Validation (Private LAN / Localhost only)   │
│ 2. Token Bucket Rate Limiter (IP-based burst rejection)    │
│ 3. Strict Input Sanitization (Path traversal rejection)     │
│ 4. Read-Only Telemetry Endpoints (Zero mutative RPCs)       │
│ 5. Isolated Background Threads (Worker isolation)          │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
ONBOARD FLIGHT CORE (Completely Autonomous & Uninterruptible)
```

---

## 2. Defensive Controls Implemented

### 2.1 Bind Address Enforcement
To prevent accidental exposure to public interfaces or wide-area networks:
- Default binding is restricted to `127.0.0.1` (loopback) or private LAN subnets (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`).
- Attempting to bind to `0.0.0.0` or public routable addresses logs an explicit warning and requires deliberate configuration override.
- Implemented in `streaming/security/access.py:is_safe_bind_address`.

### 2.2 Path Traversal & Evidence Sanitization
The Ground Monitor can request forensic evidence bundles via `GET /evidence/{evidence_id}`.
- All request parameters pass through `sanitize_evidence_id`.
- Rejects paths containing:
  - Relative navigation (`..`, `.`)
  - Directory delimiters (`/`, `\`)
  - Null bytes (`\0`)
  - Forbidden characters (`~`, `$`, `;`, `&`, `|`)
  - Exceeding 128 characters in length
- Any offending request immediately triggers HTTP `400 Bad Request` with an audit log entry.
- File system reads are strictly bounded within `storage/evidence/`.

### 2.3 Rate Limiting & Denial-of-Service Mitigation
To prevent runaway clients or socket floods from consuming onboard CPU/RAM:
- Per-IP Token Bucket rate limiter implemented in `streaming/security/rate_limit.py`.
- **Default limits:** 60 requests/minute per IP with a burst capacity of 10.
- Excessive requests are rejected with HTTP `429 Too Many Requests`.

### 2.4 Payload & Message Boundary Protections
- Event stream server enforces strict JSON decoding limits.
- Oversized query parameters and invalid UTF-8 headers are rejected gracefully without raising unhandled exceptions in the onboard runtime.
- Stream encoder bounds JPEG queue depth to 1 (drop-oldest policy), preventing memory exhaustion under network backpressure.

### 2.5 Strict Read-Only Semantics
In adherence to the core architectural invariant:
$$\text{ONBOARD} = \text{EXECUTION + ASSURANCE}, \quad \text{GROUND} = \text{OBSERVATION}$$
- No endpoints exist on either the video server (:8554) or event server (:8765) that allow modifying experiment state, overriding procedure verification, or issuing actuation commands.
- Ground Monitor is structurally unable to manipulate onboard state.

---

## 3. Automated Security Verification Suite

Security protections are validated in `tests/network/test_security.py` and benchmarked in `streaming/benchmark.py`.

### 3.1 Security Test Matrix

| Test ID | Threat Vector | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| **SEC-01** | Public bind `0.0.0.0` without override | Rejected / Warned | PASS |
| **SEC-02** | Path traversal `../../etc/passwd` | HTTP 400 Rejected | PASS |
| **SEC-03** | Windows path traversal `..\\windows\\system32` | HTTP 400 Rejected | PASS |
| **SEC-04** | Null byte injection `EVT_001\0payload` | HTTP 400 Rejected | PASS |
| **SEC-05** | Shell metacharacters `EVT_001;rm -rf /` | HTTP 400 Rejected | PASS |
| **SEC-06** | Rate limit burst test (>10 requests) | Rate Limiter Tripped | PASS |
| **SEC-07** | Malformed JSON in SSE handler | Safely Ignored / Logged | PASS |
| **SEC-08** | Dropped frame flood during slow read | Oldest Dropped, Zero Block | PASS |

### 3.2 Automated Audit Output
Generated at `storage/reports/streaming/security_report.json`:
```json
{
  "timestamp": "2026-09-13T12:00:00Z",
  "status": "PASS",
  "checks": {
    "bind_address_safety": true,
    "path_traversal_guards": true,
    "rate_limiting_enforced": true,
    "read_only_api_enforced": true
  }
}
```
