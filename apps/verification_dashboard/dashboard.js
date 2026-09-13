// ASTRA-EA Formal V&V Dashboard Frontend Logic

const VV_DATA = [
    { id: "ASTRA-SYS-001", title: "Optical Camera Stream Ingestion", cat: "FUNCTIONAL", src: "core/camera/webcam.py", test: "V-SYS-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-002", title: "Laboratory Apparatus Object Detection", cat: "FUNCTIONAL", src: "core/perception/detector.py", test: "V-SYS-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-003", title: "Hand-Object Spatial Interaction Detection", cat: "FUNCTIONAL", src: "core/interaction/geometry.py", test: "V-SYS-003-IOU", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-004", title: "Temporal Activity Dwell Accumulation", cat: "FUNCTIONAL", src: "core/temporal/buffer.py", test: "V-SYS-004-TEMPORAL", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-005", title: "Deterministic Procedure State Tracking", cat: "FUNCTIONAL", src: "core/procedure/progress.py", test: "V-SYS-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-006", title: "Tri-State Assurance Evaluation", cat: "FUNCTIONAL", src: "core/assurance/engine.py", test: "V-SYS-006-ASSURANCE", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SYS-007", title: "Cockpit Voice Guidance & Visual HUD", cat: "FUNCTIONAL", src: "core/assistance/voice.py", test: "V-SYS-007-VOICE", res: "PASS", status: "VALIDATED" },
    { id: "ASTRA-SYS-008", title: "Closed-Loop Corrective Action Recovery", cat: "FUNCTIONAL", src: "core/assistance/recovery.py", test: "V-SYS-005", res: "PASS", status: "VALIDATED" },
    { id: "ASTRA-PERF-001", title: "Pipeline Throughput >= 30.0 FPS", cat: "PERFORMANCE", src: "core/optimization/scheduler.py", test: "V-PERF-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-PERF-002", title: "End-to-End Latency <= 50.0 ms P95", cat: "PERFORMANCE", src: "core/procedure/benchmark.py", test: "V-PERF-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-PERF-003", title: "Inference Latency <= 25.0 ms P50", cat: "PERFORMANCE", src: "core/optimization/runtime.py", test: "V-PERF-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-PERF-004", title: "Memory Footprint <= 1024 MB RSS", cat: "PERFORMANCE", src: "core/optimization/soak.py", test: "V-PERF-004", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-PERF-005", title: "Cold-Boot Latency <= 5.0 s", cat: "PERFORMANCE", src: "core/cli/commands.py", test: "V-PERF-005", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-IF-001", title: "POSIX V4L2 Disconnect Detection", cat: "INTERFACE", src: "core/camera/device_manager.py", test: "V-IF-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-IF-002", title: "Vehicle Bus Interface Abstraction", cat: "INTERFACE", src: "core/integration/bus.py", test: "V-IF-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-IF-003", title: "Dual Monotonic / UTC Time Sync", cat: "INTERFACE", src: "core/mission/database.py", test: "V-IF-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-IF-004", title: "Non-Blocking Telemetry Publisher", cat: "INTERFACE", src: "core/streaming/event_server.py", test: "V-IF-004", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SAF-001", title: "Epistemic Non-Guessing Barrier", cat: "SAFETY", src: "core/assurance/engine.py", test: "V-SAF-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SAF-002", title: "Occlusion Uncertainty State Transition", cat: "SAFETY", src: "core/assurance/engine.py", test: "V-SYS-004", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SAF-003", title: "Video Stream Freeze Containment", cat: "SAFETY", src: "core/camera/device_manager.py", test: "V-SYS-006", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SAF-004", title: "Ground Network / Audio Isolation", cat: "SAFETY", src: "core/assistance/voice.py", test: "V-SYS-007", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-REL-001", title: "Auxiliary Failure Containment", cat: "RELIABILITY", src: "core/system/orchestrator.py", test: "V-REL-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-REL-002", title: "Neural Detector Heuristic Fallback", cat: "RELIABILITY", src: "core/perception/color_detector.py", test: "V-SYS-008", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-REL-003", title: "Formal Degraded Operational Modes", cat: "RELIABILITY", src: "docs/qualification/degraded-modes.md", test: "V-REL-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SEC-001", title: "100% Air-Gapped Offline Execution", cat: "SECURITY", src: "core/security/airgap.py", test: "V-SEC-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SEC-002", title: "Cryptographic SHA-256 Verification", cat: "SECURITY", src: "competition/CHECKSUMS/SHA256SUMS", test: "V-SEC-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-SEC-003", title: "Ground Streaming Read-Only Guard", cat: "SECURITY", src: "core/streaming/security.py", test: "V-SEC-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-DAT-001", title: "Microsecond SQLite WAL Logging", cat: "DATA", src: "core/mission/database.py", test: "V-DAT-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-DAT-002", title: "Causal Provenance Evidence Chain", cat: "DATA", src: "core/procedure/traceability.py", test: "V-DAT-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-DAT-003", title: "Bounded Storage Write Rate <= 10MB/s", cat: "DATA", src: "storage/storage_manager.py", test: "V-DAT-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-OPS-001", title: "Cockpit HUD High Contrast Visuals", cat: "OPERATIONS", src: "core/gui/console.py", test: "V-OPS-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-OPS-002", title: "Speech Articulation Rate Compliance", cat: "OPERATIONS", src: "core/assistance/voice.py", test: "V-OPS-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-OPS-003", title: "Pre-Flight Self-Test Execution < 3s", cat: "OPERATIONS", src: "core/cli/commands.py", test: "V-OPS-003", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-ENV-001", title: "Illumination Invariance (45-850 Lux)", cat: "ENVIRONMENTAL", src: "core/camera/profile.py", test: "V-ENV-001", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-ENV-002", title: "Multi-Angle View Invariance (35-65 deg)", cat: "ENVIRONMENTAL", src: "core/camera/profile.py", test: "V-ENV-002", res: "PASS", status: "VERIFIED" },
    { id: "ASTRA-ENV-003", title: "Launch Vibration Survival (14.1 Grms)", cat: "ENVIRONMENTAL", src: "docs/qualification/environmental-test-plan.md", test: "V-ENV-003", res: "DEFERRED", status: "DEFERRED" },
    { id: "ASTRA-ENV-004", title: "Thermal-Vacuum Cycling (-20 to +60C)", cat: "ENVIRONMENTAL", src: "docs/qualification/environmental-test-plan.md", test: "V-ENV-004", res: "DEFERRED", status: "DEFERRED" },
    { id: "ASTRA-ENV-005", title: "Radiation TID Tolerance (50 krad)", cat: "ENVIRONMENTAL", src: "docs/qualification/environmental-test-plan.md", test: "V-ENV-005", res: "DEFERRED", status: "DEFERRED" }
];

document.addEventListener("DOMContentLoaded", () => {
    const tableBody = document.getElementById("table-body");
    const filterInput = document.getElementById("filter-input");
    const timestampElem = document.getElementById("live-timestamp");

    if (timestampElem) {
        timestampElem.innerText = new Date().toISOString();
    }

    function renderTable(data) {
        tableBody.innerHTML = "";
        data.forEach(item => {
            const tr = document.createElement("tr");
            const badgeClass = item.res === "PASS" ? "badge-pass" : "badge-deferred";
            tr.innerHTML = `
                <td><strong><code>${item.id}</code></strong></td>
                <td>${item.title}</td>
                <td>${item.cat}</td>
                <td><code>${item.src}</code></td>
                <td><code>${item.test}</code></td>
                <td><span class="${badgeClass}">${item.res}</span></td>
                <td><span class="${badgeClass}">${item.status}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }

    renderTable(VV_DATA);

    filterInput.addEventListener("input", (e) => {
        const q = e.target.value.toLowerCase().trim();
        const filtered = VV_DATA.filter(item => 
            item.id.toLowerCase().includes(q) ||
            item.title.toLowerCase().includes(q) ||
            item.cat.toLowerCase().includes(q) ||
            item.src.toLowerCase().includes(q) ||
            item.test.toLowerCase().includes(q)
        );
        renderTable(filtered);
    });
});
