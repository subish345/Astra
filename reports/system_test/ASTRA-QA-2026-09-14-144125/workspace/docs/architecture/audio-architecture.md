# ASTRA-EA — Audio UX & Voice Guidance Architecture

## Local Offline Speech Synthesis & Notification Engine

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Objectives & Ground Rules

1. **Air-Gapped Operation**: 100% local text-to-speech synthesis using offline libraries (`pyttsx3`). Zero reliance on external cloud APIs or network interfaces.
2. **Priority Preemption**: Emergency deviations and critical alerts immediately preempt lower-priority speech without delay.
3. **Deduplication Cooldowns**: Spoken notifications are throttled by message content and priority level to prevent distracting repetition.
4. **Resilient Fallback**: Audio hardware failures or headless execution environments gracefully fall back to silent mock operation without crashing the host application.

---

## 2. Priority Hierarchy & Cooldown Policy

[`AudioPolicy`](file:///home/subish-loq/Documents/astra/core/voice/policies.py) defines strict operational timing:

| Priority | Numeric Value | Default Cooldown | Preemption Behavior | Operational Usage |
|---|:---:|:---:|---|---|
| `CRITICAL` | 1 | **2.0s** | **Purges pending queue**, interrupts current speech | Severe procedure deviation, immediate experiment stop |
| `WARNING` | 2 | **5.0s** | Queues ahead of guidance and info | Wrong object selected, timeout caution |
| `GUIDANCE` | 3 | **3.5s** | Standard queue order | Next step instructions, recovery directions |
| `INFO` | 4 | **10.0s** | Lowest queue order | Step completed confirmation, system status notices |

---

## 3. Subsystem Architecture

```text
core/voice/
├── __init__.py              # Unified subsystem exports
├── interface.py             # VoiceProvider interface & AudioPriority enum
├── policies.py              # AudioPolicy & AudioDeduplicator
├── offline_tts.py           # OfflineTTSProvider (pyttsx3 wrapper with headless fallback)
└── manager.py               # AudioQueueManager (thread-safe PriorityQueue worker)
```

### Synthesis Flow:
```text
Client Call: manager.speak("Warning: wrong object", priority=WARNING)
     ↓
AudioDeduplicator.should_speak(...)
     ├── If within cooldown (< 5.0s) ──> Suppressed (Returns False)
     └── If allowed:
             ↓
PriorityQueue.put((2, timestamp, text, WARNING))
             ↓
Worker Daemon Thread:
     ├── Fetches highest-priority item
     ├── If CRITICAL: purges non-critical pending items
     └── Invokes OfflineTTSProvider.speak(...)
             ↓
Dispatches on_spoken callback to UI / Mission Log
```
