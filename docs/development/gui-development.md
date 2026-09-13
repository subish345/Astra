# ASTRA-EA — GUI Development Guide

## Extending and Customizing the Mission Console

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Development Principles

When adding features or widgets to the Mission Console:
1. **Preserve Decoupling**: Do NOT add inference algorithms, OpenCV detectors, or procedure rules inside widget classes.
2. **Follow the Event Bus Pattern**:
   - Backend algorithms emit typed events via [`BackendEventBridge`](file:///home/subish-loq/Documents/astra/core/ui/bridge.py).
   - [`MissionUIState`](file:///home/subish-loq/Documents/astra/core/ui/state.py) updates its presentation data structures.
   - UI widgets observe state changes and update labels/tables.
3. **Use Space-Operations Theme Tokens**: Reference [`core.ui.theme.Colors`](file:///home/subish-loq/Documents/astra/core/ui/theme.py) for all color assignments. Avoid hardcoding ad-hoc hex colors.

---

## 2. Launching the Mission Console

```bash
# Launch interactive Mission Console on default camera (/dev/video0)
python3 main.py mission

# Launch on recorded video with right-side camera profile
python3 main.py mission --source storage/video/demo.mp4 --camera-profile view_right

# Launch in fullscreen mode
python3 main.py mission --fullscreen
```

---

## 3. Adding a New Mission View

To add a new screen (e.g. `TelemetryView`):
1. Create `core/ui/views/telemetry_view.py` inheriting from `QWidget`.
2. Add the view to `MissionConsoleWindow.stack` in [`core/ui/main_window.py`](file:///home/subish-loq/Documents/astra/core/ui/main_window.py).
3. Add a navigation button to the sidebar navigation panel.
4. Add unit test in `tests/gui/`.
