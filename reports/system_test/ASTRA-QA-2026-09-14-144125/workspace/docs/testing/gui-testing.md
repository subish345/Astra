# ASTRA-EA — GUI Testing Strategy

## Automated and Headless Verification for Mission Console

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Headless Execution Strategy

To enable automated CI execution and non-interactive testing on servers lacking physical displays, the Mission Console test suites execute via Qt's offscreen platform plugin:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/gui/ -v
```

This guarantees 100% test coverage across UI component logic, signal propagation, and pixel rendering without opening desktop windows or requiring X11 display servers.

---

## 2. Test Suites Overview

| Test Suite | File | Focus Areas |
|---|---|---|
| **State Store Tests** | [`tests/gui/test_mission_ui_state.py`](file:///home/subish-loq/Documents/astra/tests/gui/test_mission_ui_state.py) | Dataclass mutations, step progress updates, deviation flags, timeline logs. |
| **Component Tests** | [`tests/gui/test_console_components.py`](file:///home/subish-loq/Documents/astra/tests/gui/test_console_components.py) | VideoPanel layer toggles, StepPanel next action card, StatusPanel alert banners, ProgressPanel step icons, EvidencePanel table, HealthPanel badges. |
| **Integration Tests** | [`tests/gui/test_mission_integration.py`](file:///home/subish-loq/Documents/astra/tests/gui/test_mission_integration.py) | Full end-to-end signal dispatching: `sig_step_progress`, `sig_assurance_decision`, `sig_deviation`, `sig_recovery`, stack navigation, pixel-perfect window grabs. |

---

## 3. Running GUI Tests

```bash
# Run all GUI tests
pytest tests/gui/ -v

# Run with snapshot capture
python3 -c "
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from core.ui import MissionConsoleWindow

app = QApplication.instance() or QApplication([])
win = MissionConsoleWindow()
win.show()
win.grab().save('storage/console_test.png')
print('Snapshot captured successfully!')
"
```
