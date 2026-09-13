# ASTRA-EA Development & Engineering Workflow

## 1. Environment Setup

### 1.1 Prerequisites
- Linux OS (Fedora, Ubuntu, or RHEL)
- Python 3.11+ (Python 3.14 on development machine)
- Git
- Camera device (e.g. `/dev/video0`) or video files for simulation

### 1.2 Virtual Environment & Dependencies
```bash
# Clone and enter directory
cd /home/subish-loq/Documents/astra

# Optional: Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install editable package
pip install -e .
```

---

## 2. Standard CLI Workflows

ASTRA-EA provides a centralized CLI entrypoint via `main.py` (or `astra` command when installed):

```bash
# 1. Run system diagnostics (Hardware, GPU, Camera, DB, Config)
python3 main.py doctor

# 2. Validate all system configuration files
python3 main.py config validate

# 3. Validate experiment definition schema
python3 main.py experiment validate configs/experiments/demo.yaml

# 4. Initialize local SQLite audit database
python3 main.py db init

# 5. Test camera stream connectivity and report FPS/resolution
python3 main.py camera test --source 0

# 6. Check system version
python3 main.py version
```

---

## 3. Testing Workflow

Execute automated tests using `pytest`:

```bash
# Run complete test suite
python3 -m pytest tests/ -v

# Run unit tests only
python3 -m pytest tests/unit/ -v

# Run integration tests
python3 -m pytest tests/integration/ -v
```

---

## 4. Engineering Conventions

### 4.1 Anti-Hallucination & Anti-Fake Rule
- Never hardcode mock strings like `return "VERIFIED"` to simulate working AI models.
- If a model is not yet trained/implemented, clearly label the stub with `source = "STUB"` or `source = "SIMULATION"`.
- Never present fake benchmark numbers or fabricated accuracies.

### 4.2 Configuration-First Rule
- Never hardcode experiment steps, object lists, or confidence thresholds in Python code.
- All experiment sequence rules must reside in `configs/experiments/*.yaml`.

### 4.3 Git Commit Conventions
Follow conventional commit standards:
- `chore: establish foundation ...`
- `feat(procedure): implement schema validation ...`
- `test(camera): add mocked device unit test ...`
- `docs(requirements): update traceability matrix ...`
