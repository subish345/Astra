"""Command-Line Interface (CLI) foundation for ASTRA-EA.

Provides operational and diagnostic commands:
  astra doctor
  astra config validate
  astra experiment validate <path>
  astra db init
  astra camera test
  astra version
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional
import cv2

from core.camera.file_source import VideoFileSource
from core.camera.webcam import WebcamSource
from core.common.config import get_project_root, load_camera_config, load_config
from core.common.logging import setup_logging
from core.mission.database import DatabaseManager
from core.procedure.validator import ProcedureValidationError, load_procedure_file
from storage.storage_manager import StorageManager

VERSION = "0.1.0"


def cmd_version(args: argparse.Namespace) -> int:
    """Print ASTRA-EA version and project identity."""
    print("=" * 60)
    print("ASTRA-EA — Autonomous Spacecraft Experiment Assurance & Assistance")
    print("Tagline: 'See. Understand. Verify. Assist. Record. — Locally, in Space.'")
    print(f"Version: v{VERSION} (Phase 0/1 Engineering Foundation)")
    print("Status: Engineering-grade ground demonstrator (SIH26174)")
    print("=" * 60)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run comprehensive system diagnostic checks."""
    print("============================================================")
    print(" ASTRA-EA SYSTEM DIAGNOSTIC (DOCTOR)")
    print("============================================================")

    all_passed = True

    # 1. Python environment
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    status_icon = "✓" if py_ok else "✗"
    print(f"[{status_icon}] Python Runtime: {py_ver} ({'PASS' if py_ok else 'FAIL: Python 3.11+ required'})")
    if not py_ok:
        all_passed = False

    # 2. PyTorch & CUDA check (HONEST: No fake AI)
    try:
        import torch  # type: ignore
        cuda_avail = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU only"
        print(f"[✓] PyTorch: {torch.__version__} (CUDA: {cuda_avail}, Device: {device_name})")
    except ImportError:
        # Check if nvidia-smi exists on host
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                smi_out = subprocess.check_output(
                    [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    text=True,
                    timeout=3,
                ).strip()
                print(f"[-] PyTorch: NOT_INSTALLED in active environment (Host GPU detected: {smi_out})")
            except Exception:
                print("[-] PyTorch: NOT_INSTALLED in active environment (Host GPU: query failed)")
        else:
            print("[-] PyTorch: NOT_INSTALLED (CPU / Host compute only)")

    # 3. OpenCV
    print(f"[✓] OpenCV: {cv2.__version__}")

    # 4. Configuration validation
    root = get_project_root()
    sys_cfg_path = root / "configs/system.yaml"
    if sys_cfg_path.exists():
        try:
            cfg = load_config(sys_cfg_path)
            print(f"[✓] System Configuration: Valid ({sys_cfg_path.relative_to(root)})")
        except Exception as exc:
            print(f"[✗] System Configuration Error: {exc}")
            all_passed = False
    else:
        print(f"[✗] System Configuration Missing: {sys_cfg_path}")
        all_passed = False

    # 5. Database check
    db_path = root / "storage/database/astra.db"
    try:
        db = DatabaseManager(db_path)
        db.initialize()
        with db.get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM schema_migrations")
            count = cur.fetchone()[0]
        print(f"[✓] SQLite Database: Initialized and readable ({db_path.relative_to(root)}, migrations: {count})")
    except Exception as exc:
        print(f"[✗] SQLite Database Failure: {exc}")
        all_passed = False

    # 6. Storage filesystem check
    try:
        storage = StorageManager(project_root=root)
        metrics = storage.get_storage_metrics()
        print(f"[✓] Storage Subsystem: Writable (Used: {metrics['storage_used_gb']} GB, Free: {metrics['disk_free_gb']} GB)")
    except Exception as exc:
        print(f"[✗] Storage Subsystem Failure: {exc}")
        all_passed = False

    # 7. Camera hardware check
    cam_device = 0
    cap = cv2.VideoCapture(cam_device)
    if cap and cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        print(f"[✓] Camera Device {cam_device}: ONLINE ({w}x{h} @ {fps:.1f} FPS)")
    else:
        print(f"[-] Camera Device {cam_device}: UNAVAILABLE or PERMISSION DENIED (Use VideoFileSource for simulation)")

    print("============================================================")
    if all_passed:
        print("Diagnostic Result: ALL FOUNDATION CHECKS PASSED.")
        return 0
    else:
        print("Diagnostic Result: ONE OR MORE CHECKS REPORTED ISSUES.")
        return 1


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate all system and device configuration files."""
    root = get_project_root()
    print("Validating configuration files...")
    all_ok = True

    # 1. system.yaml
    sys_path = root / "configs/system.yaml"
    try:
        cfg = load_config(sys_path)
        print(f"✓ {sys_path.relative_to(root)}: OK (Environment: {cfg.system.environment})")
    except Exception as exc:
        print(f"✗ {sys_path.relative_to(root)}: FAILED ({exc})")
        all_ok = False

    # 2. cameras/default.yaml
    cam_path = root / "configs/cameras/default.yaml"
    try:
        cam_cfg = load_camera_config(cam_path)
        print(f"✓ {cam_path.relative_to(root)}: OK (Source: {cam_cfg.source_type}, Resolution: {cam_cfg.width}x{cam_cfg.height})")
    except Exception as exc:
        print(f"✗ {cam_path.relative_to(root)}: FAILED ({exc})")
        all_ok = False

    return 0 if all_ok else 1


def cmd_experiment_validate(args: argparse.Namespace) -> int:
    """Validate an experiment procedure YAML against Pydantic schema and semantic rules."""
    path = Path(args.path)
    root = get_project_root()
    if not path.is_absolute():
        path = root / path

    print(f"Validating experiment procedure: {path.name}...")
    try:
        exp = load_procedure_file(path)
        print(f"✓ Validation SUCCESSFUL: {exp.experiment.id} ('{exp.experiment.name}')")
        print(f"  - Version: {exp.experiment.version}")
        print(f"  - Objects Defined: {len(exp.objects)} ({', '.join(o.id for o in exp.objects)})")
        print(f"  - Steps Defined: {len(exp.steps)}")
        for step in exp.steps:
            print(f"    [{step.sequence}] {step.id}: {step.name} (Actions: {', '.join(step.expected_actions)})")
        return 0
    except FileNotFoundError:
        print(f"✗ Error: File not found at {path}")
        return 1
    except ProcedureValidationError as exc:
        print("✗ Procedure Validation FAILED:")
        for err in exc.errors:
            print(f"  - {err}")
        return 1
    except Exception as exc:
        print(f"✗ Unexpected Error: {exc}")
        return 1


def cmd_db_init(args: argparse.Namespace) -> int:
    """Initialize or verify the SQLite database schema."""
    root = get_project_root()
    db_path = root / "storage/database/astra.db"
    print(f"Initializing ASTRA-EA database at {db_path}...")
    try:
        db = DatabaseManager(db_path)
        db.initialize()
        print("✓ Database initialization complete.")
        return 0
    except Exception as exc:
        print(f"✗ Database initialization failed: {exc}")
        return 1


def cmd_camera_test(args: argparse.Namespace) -> int:
    """Test video capture device and measure frame throughput."""
    source_id = args.source
    frames_to_read = args.frames

    print(f"Testing camera source '{source_id}' (Sampling {frames_to_read} frames)...")

    # Determine if source is integer (device index) or file path
    try:
        device_idx = int(source_id)
        cap = cv2.VideoCapture(device_idx)
    except ValueError:
        cap = cv2.VideoCapture(source_id)

    if not cap or not cap.isOpened():
        print(f"✗ Unable to open camera source: {source_id}")
        return 1

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    configured_fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"✓ Camera opened successfully. Stream: {width}x{height} (Configured FPS: {configured_fps:.1f})")

    t_start = time.time()
    read_count = 0

    for _ in range(frames_to_read):
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        read_count += 1

    elapsed = time.time() - t_start
    cap.release()

    if read_count == 0:
        print("✗ Failed to capture any frames.")
        return 1

    observed_fps = read_count / elapsed if elapsed > 0 else 0.0
    print(f"✓ Captured {read_count}/{frames_to_read} frames in {elapsed:.2f}s (Effective FPS: {observed_fps:.1f})")
    return 0


def cmd_camera_list(args: argparse.Namespace) -> int:
    """Discover and probe locally accessible video capture devices."""
    print("============================================================")
    print(" ASTRA-EA LOCAL CAMERA DISCOVERY")
    print("============================================================")

    found_any = False
    # Check device nodes on system
    video_nodes = sorted(Path("/dev").glob("video*"))
    if video_nodes:
        for node in video_nodes:
            try:
                idx = int("".join(filter(str.isdigit, node.name)))
            except ValueError:
                continue

            cap = cv2.VideoCapture(idx)
            if cap and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                cap.release()
                found_any = True
                print(f"Camera Device {idx} ({node}):")
                print(f"  Status:     AVAILABLE")
                print(f"  Resolution: {w}x{h}")
                print(f"  FPS:        {fps:.1f}")
                print(f"  Backend:    OpenCV (V4L2 / UVC)")
                print("-" * 40)
            else:
                print(f"Camera Device {idx} ({node}):")
                print(f"  Status:     UNAVAILABLE")
                print(f"  Reason:     Device node exists but could not be opened")
                print("-" * 40)
    else:
        # Fallback for non-Linux or virtual environments without /dev
        for idx in range(2):
            cap = cv2.VideoCapture(idx)
            if cap and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                cap.release()
                found_any = True
                print(f"Camera Device {idx}:")
                print(f"  Status:     AVAILABLE")
                print(f"  Resolution: {w}x{h}")
                print(f"  FPS:        {fps:.1f}")
                print(f"  Backend:    OpenCV")
                print("-" * 40)

    if not found_any:
        print("[-] No hardware camera streams detected. Use VideoFileSource for video simulation.")
    print("============================================================")
    return 0


def cmd_perception_test(args: argparse.Namespace) -> int:
    """Run perception pipeline on live camera or video file."""
    source_arg = args.source
    max_frames = args.frames
    detector_type = args.detector.lower()
    run_benchmark = args.benchmark
    no_display = args.no_display

    root = get_project_root()
    cfg = load_config()

    print("============================================================")
    print(" ASTRA-EA PERCEPTION SUBSYSTEM TEST")
    print("============================================================")
    print(f"Source:           {source_arg}")
    print(f"Target Frames:    {max_frames}")
    print(f"Detector Backend: {detector_type}")
    print(f"Mode:             {'BENCHMARK' if run_benchmark else 'LIVE MONITOR'}")
    print("-" * 60)

    # 1. Initialize Video Source
    try:
        dev_idx = int(source_arg)
        source = WebcamSource(device_id=dev_idx, width=640, height=480, fps=30)
    except ValueError:
        source_path = Path(source_arg)
        if not source_path.is_absolute():
            source_path = root / source_path
        source = VideoFileSource(file_path=source_path, loop=True)

    if not source.start():
        print(f"✗ Failed to initialize video source: {source_arg}")
        return 1

    # 2. Initialize Models & Adapters
    if detector_type == "yolo":
        yolo_path = root / (cfg.perception.yolo_model_path or "models/checkpoints/detector.onnx")
        try:
            from core.perception.detection.yolo_adapter import YOLOAdapter
            detector = YOLOAdapter(yolo_path, device=cfg.perception.device)
        except Exception as exc:
            print(f"[-] YOLO initialization failed: {exc}. Falling back to ColorSpatialObjectDetector.")
            from core.perception.detection.color_adapter import ColorSpatialObjectDetector
            detector = ColorSpatialObjectDetector()
    else:
        from core.perception.detection.color_adapter import ColorSpatialObjectDetector
        detector = ColorSpatialObjectDetector()

    from core.perception.hands.adapter import LightweightHandDetector
    from core.perception.pipeline import PerceptionPipeline
    from core.perception.pose.adapter import LightweightPoseEstimator
    from core.perception.scheduler import PerceptionScheduler, SchedulerConfig
    from core.perception.tracking.tracker import MultiObjectTracker
    from core.perception.visualizer import PerceptionVisualizer

    pose_est = LightweightPoseEstimator()
    hand_det = LightweightHandDetector()
    tracker = MultiObjectTracker(iou_threshold=cfg.perception.iou_threshold, max_lost_frames=cfg.perception.max_lost_frames)

    sched_cfg = SchedulerConfig(
        tracking_interval=cfg.perception.tracking_interval,
        detection_interval=cfg.perception.detection_interval,
        pose_interval=cfg.perception.pose_interval,
        hand_interval=cfg.perception.hand_interval,
        quality_interval=cfg.perception.quality_interval,
    )
    scheduler = PerceptionScheduler(sched_cfg)
    pipeline = PerceptionPipeline(
        detector=detector,
        pose_estimator=pose_est,
        hand_detector=hand_det,
        tracker=tracker,
        scheduler=scheduler,
    )

    # 3. Benchmark Mode
    if run_benchmark:
        from core.perception.benchmark import PerceptionBenchmark
        bm = PerceptionBenchmark(pipeline=pipeline, camera_source=source)
        print("Executing benchmark runs...")
        report = bm.run(max_frames=max_frames)
        print(report.format_text())
        source.stop()
        return 0

    # 4. Live Perception Loop
    from core.camera.ingestion import FramePacket
    visualizer = PerceptionVisualizer()

    frames_processed = 0
    t_start = time.time()

    print(f"Perception active using {detector.model_name}. Press 'q' or Ctrl+C to stop.")

    try:
        while frames_processed < max_frames:
            fd = source.read()
            if fd is None:
                if not source.is_active:
                    break
                time.sleep(0.005)
                continue

            packet = FramePacket.from_frame_data(fd, capture_fps=source.get_fps())
            state = pipeline.process_frame(packet)
            frames_processed += 1

            if not no_display:
                vis = visualizer.render(packet.image, state)
                cv2.imshow("ASTRA-EA Perception Monitor (Phase 2)", vis)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
            else:
                if frames_processed % 10 == 0:
                    objs = ", ".join(f"{t.class_name}#{t.track_id}" for t in state.tracks if t.is_active) or "None"
                    print(
                        f"Frame #{state.frame_id:4d} | FPS: {state.fps:4.1f} | Latency: {state.latency.total_ms:5.1f}ms | Active Tracks: {objs}"
                    )

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        source.stop()
        if not no_display:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

    elapsed = time.time() - t_start
    effective_fps = frames_processed / elapsed if elapsed > 0 else 0.0
    print("-" * 60)
    print(f"Completed {frames_processed} frames in {elapsed:.2f}s (Effective Throughput: {effective_fps:.1f} FPS)")
    print("============================================================")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="astra",
        description="ASTRA-EA — Autonomous Spacecraft Experiment Assurance & Assistance CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # version
    p_ver = subparsers.add_parser("version", help="Print system version and status")
    p_ver.set_defaults(func=cmd_version)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run system diagnostics and environment checks")
    p_doc.set_defaults(func=cmd_doctor)

    # config
    p_cfg = subparsers.add_parser("config", help="Configuration management")
    cfg_subs = p_cfg.add_subparsers(dest="config_cmd")
    p_cfg_val = cfg_subs.add_parser("validate", help="Validate YAML configuration files")
    p_cfg_val.set_defaults(func=cmd_config_validate)

    # experiment
    p_exp = subparsers.add_parser("experiment", help="Experiment procedure operations")
    exp_subs = p_exp.add_subparsers(dest="exp_cmd")
    p_exp_val = exp_subs.add_parser("validate", help="Validate an experiment procedure YAML")
    p_exp_val.add_argument("path", default="configs/experiments/demo.yaml", nargs="?", help="Path to procedure YAML")
    p_exp_val.set_defaults(func=cmd_experiment_validate)

    # db
    p_db = subparsers.add_parser("db", help="Database management")
    db_subs = p_db.add_subparsers(dest="db_cmd")
    p_db_init = db_subs.add_parser("init", help="Initialize SQLite tables")
    p_db_init.set_defaults(func=cmd_db_init)

    # camera
    p_cam = subparsers.add_parser("camera", help="Camera device management")
    cam_subs = p_cam.add_subparsers(dest="camera_cmd")
    p_cam_list = cam_subs.add_parser("list", help="Discover and list available cameras")
    p_cam_list.set_defaults(func=cmd_camera_list)
    p_cam_test = cam_subs.add_parser("test", help="Test camera connection and FPS")
    p_cam_test.add_argument("--source", default="0", help="Camera index or video file path")
    p_cam_test.add_argument("--frames", type=int, default=30, help="Number of frames to sample")
    p_cam_test.set_defaults(func=cmd_camera_test)

    # perception
    p_perc = subparsers.add_parser("perception", help="Perception subsystem operations")
    perc_subs = p_perc.add_subparsers(dest="perception_cmd")
    p_perc_test = perc_subs.add_parser("test", help="Run perception pipeline test")
    p_perc_test.add_argument("--source", default="0", help="Camera index or video file path")
    p_perc_test.add_argument("--frames", type=int, default=60, help="Max frames to process")
    p_perc_test.add_argument("--detector", default="color_spatial", choices=["color_spatial", "yolo"], help="Detector backend")
    p_perc_test.add_argument("--benchmark", action="store_true", help="Run performance benchmark")
    p_perc_test.add_argument("--no-display", action="store_true", help="Disable OpenCV GUI window")
    p_perc_test.set_defaults(func=cmd_perception_test)

    return parser


def cli() -> None:
    """Main CLI entrypoint."""
    setup_logging(level="WARNING")
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        sys.exit(args.func(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
