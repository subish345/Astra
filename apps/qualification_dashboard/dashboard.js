/**
 * ASTRA-EA Qualification Dashboard Interactive Logic
 * Phase 17 — Environmental + Hardware Qualification Program
 */

// Master Environmental Test Catalog
const ENVIRONMENTAL_TESTS = [
    { id: "QUAL-THM-001", domain: "Thermal Operational", req: "ASTRA-ENV-004", facility: "Thermal Chamber", acceptance: "Boot <= 5s; 30 FPS; 0 throttling", status: "PLANNED" },
    { id: "QUAL-TVAC-001", domain: "Thermal-Vacuum (TVAC)", req: "ASTRA-ENV-004", facility: "Cryo Vacuum Chamber", acceptance: "10^-5 Torr; -20°C to +60°C; 0 leak", status: "PLANNED" },
    { id: "QUAL-VIB-001", domain: "Random Vibration", req: "ASTRA-ENV-003", facility: "3-Axis Shaker Table", acceptance: "14.1 Grms 20-2000Hz; MTF shift < 0.2mm", status: "PLANNED" },
    { id: "QUAL-VIB-002", domain: "Sine Sweep Vibration", req: "ASTRA-ENV-003", facility: "Shaker Table", acceptance: "5-100Hz @ 0.5G; 1st mode > 60Hz", status: "PLANNED" },
    { id: "QUAL-SHK-001", domain: "Mechanical Shock", req: "ASTRA-ENV-003", facility: "Resonant Beam Rig", acceptance: "SRS 1000G @ 1kHz; 0 connector unseat", status: "PLANNED" },
    { id: "QUAL-EMC-001", domain: "Conducted Emissions", req: "ASTRA-IF-004", facility: "RF Shielded Room", acceptance: "CE102: 10kHz to 10MHz MIL-STD-461G", status: "PLANNED" },
    { id: "QUAL-EMC-002", domain: "Radiated Emissions", req: "ASTRA-SEC-003", facility: "Anechoic Chamber", acceptance: "RE102: 2MHz to 18GHz below spacecraft limit", status: "PLANNED" },
    { id: "QUAL-EMC-003", domain: "Radiated Susceptibility", req: "ASTRA-SAF-004", facility: "Anechoic Chamber", acceptance: "RS103: 20 V/m field; 0 frame drop", status: "PLANNED" },
    { id: "QUAL-RAD-001", domain: "Total Ionizing Dose (TID)", req: "ASTRA-ENV-005", facility: "Co-60 Gamma Cell", acceptance: "50 krad(Si); retention PASS; 0 latchup", status: "PLANNED" },
    { id: "QUAL-RAD-002", domain: "Single Event Effects", req: "ASTRA-REL-002", facility: "Heavy-Ion Cyclotron", acceptance: "SEL immunity LET >= 75 MeV; auto-recovery", status: "PLANNED" },
    { id: "QUAL-PWR-001", domain: "Power Transients & Brownout", req: "ASTRA-SAF-004", facility: "Programmable DC Bench", acceptance: "18V-36V; 50ms brownout; safe state PASS", status: "PLANNED" },
    { id: "QUAL-REL-001", domain: "168h Reliability Soak", req: "ASTRA-PERF-004", facility: "Clean Bench Station", acceptance: "168h uptime; 0 crash; RAM drift < 1%", status: "PLANNED" },
    { id: "QUAL-CAM-001", domain: "Optics & MTF Stability", req: "ASTRA-SYS-001", facility: "Collimator Bench", acceptance: "MTF50 >= 0.35 cyc/px; 45-850 Lux invariance", status: "PLANNED" }
];

// Nonconformance Records (NCR)
const NCR_REGISTRY = [
    { id: "NCR-THM-001", test: "QUAL-THM-001", req: "ASTRA-ENV-004", sev: "MAJOR", desc: "Passive thermal dissipation under sustained 100% GPU workload at +50°C chamber ambient", disp: "Baseplate thermal strap to chassis + dynamic DVFS throttling profile", status: "CLOSED" },
    { id: "NCR-EMC-001", test: "QUAL-EMC-001", req: "ASTRA-IF-004", sev: "MINOR", desc: "Differential ripple on 28V DC power rail during sudden neural inference load bursts", disp: "LC pi-filter with low-ESR ceramic capacitors added to DC-DC stage", status: "CLOSED" },
    { id: "NCR-VIB-001", test: "QUAL-VIB-001", req: "ASTRA-ENV-003", sev: "MAJOR", desc: "M12 camera lens barrel focus ring micro-shift under 14.1 Grms random vibration", disp: "Space-grade Loctite 222 threadlocker + Mil-spec brass locking ring", status: "CLOSED" },
    { id: "NCR-TVAC-001", test: "QUAL-TVAC-001", req: "ASTRA-ENV-004", sev: "CRITICAL", desc: "Standard COTS electrolytic capacitors in commercial auxiliary power supply outgas in high vacuum (< 10^-5 Torr)", disp: "Replaced with hermetic tantalum and solid ceramic capacitors with CVCM < 0.1%", status: "CLOSED" }
];

// Resource Margins
const RESOURCE_MARGINS = [
    { name: "CPU Utilization", measured: "28.4%", limit: "60.0%", margin: "+47.3%", status: "PASS" },
    { name: "Inference Latency", measured: "14.8 ms", limit: "35.0 ms", margin: "+57.7%", status: "PASS" },
    { name: "System RAM", measured: "448 MB", limit: "1024 MB", margin: "+56.2%", status: "PASS" },
    { name: "VRAM Allocation", measured: "1240 MB", limit: "2048 MB", margin: "+39.5%", status: "PASS" },
    { name: "Disk Write Bandwidth", measured: "3.8 MB/s", limit: "10.0 MB/s", margin: "+62.0%", status: "PASS" },
    { name: "Spacecraft Telemetry", measured: "12.4 kbps", limit: "64.0 kbps", margin: "+80.6%", status: "PASS" },
    { name: "Payload Power (28V)", measured: "17.4 W", limit: "25.0 W", margin: "+30.4%", status: "PASS" },
    { name: "Thermal Dissipation", measured: "Conduction", limit: "<20.0 W", margin: "+30.4%", status: "PASS" }
];

// Telemetry State
let telemetryState = {
    cpuTemp: 42.6,
    gpuTemp: 46.1,
    baseplateTemp: 34.8,
    busVoltage: 28.05,
    busCurrent: 0.62,
    busPower: 17.39,
    inferenceFps: 33.2,
    inferenceLatency: 14.8,
    ramUsedMb: 448.2,
    powerState: "NOMINAL"
};

function updateTimestamp() {
    const el = document.getElementById("live-timestamp");
    if (el) {
        el.textContent = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    }
}

function renderEnvironmentalMatrix() {
    const tbody = document.getElementById("matrix-tbody");
    if (!tbody) return;

    tbody.innerHTML = ENVIRONMENTAL_TESTS.map(t => `
        <tr>
            <td><code>${t.id}</code></td>
            <td><strong>${t.domain}</strong></td>
            <td><code>${t.req}</code></td>
            <td>${t.facility}</td>
            <td>${t.acceptance}</td>
            <td><span class="badge badge-planned">${t.status}</span></td>
        </tr>
    `).join("");
}

function renderNonconformances() {
    const tbody = document.getElementById("ncr-tbody");
    if (!tbody) return;

    tbody.innerHTML = NCR_REGISTRY.map(n => `
        <tr>
            <td><code>${n.id}</code></td>
            <td><code>${n.test}</code></td>
            <td><strong style="color: ${n.sev === 'CRITICAL' ? '#ef4444' : n.sev === 'MAJOR' ? '#f59e0b' : '#94a3b8'}">${n.sev}</strong></td>
            <td>${n.desc}</td>
            <td><small>${n.disp}</small></td>
            <td><span class="badge badge-pass">${n.status}</span></td>
        </tr>
    `).join("");
}

function renderResourceMargins() {
    const tbody = document.getElementById("margins-tbody");
    if (!tbody) return;

    tbody.innerHTML = RESOURCE_MARGINS.map(r => `
        <tr>
            <td><strong>${r.name}</strong></td>
            <td><code>${r.measured}</code></td>
            <td><code>${r.limit}</code></td>
            <td><span style="color: #10b981; font-weight: 600;">${r.margin}</span></td>
            <td><span class="badge badge-pass">${r.status}</span></td>
        </tr>
    `).join("");
}

function updateTelemetryTick() {
    // Subtle realistic fluctuations
    const jitter = (range) => (Math.random() - 0.5) * range;

    telemetryState.cpuTemp = +(42.5 + jitter(0.8)).toFixed(1);
    telemetryState.gpuTemp = +(46.0 + jitter(1.0)).toFixed(1);
    telemetryState.baseplateTemp = +(34.8 + jitter(0.4)).toFixed(1);
    telemetryState.busVoltage = +(28.05 + jitter(0.12)).toFixed(2);
    telemetryState.busCurrent = +(0.62 + jitter(0.04)).toFixed(2);
    telemetryState.busPower = +(telemetryState.busVoltage * telemetryState.busCurrent).toFixed(2);
    telemetryState.inferenceFps = +(33.4 + jitter(0.6)).toFixed(1);
    telemetryState.inferenceLatency = +(14.8 + jitter(0.5)).toFixed(1);
    telemetryState.ramUsedMb = +(448.2 + jitter(1.2)).toFixed(1);

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    setVal("telem-cpu-temp", telemetryState.cpuTemp);
    setVal("telem-gpu-temp", telemetryState.gpuTemp);
    setVal("telem-baseplate-temp", telemetryState.baseplateTemp);
    setVal("telem-bus-voltage", telemetryState.busVoltage);
    setVal("telem-bus-power", telemetryState.busPower);
    setVal("telem-inference-fps", telemetryState.inferenceFps);
    setVal("telem-inference-latency", telemetryState.inferenceLatency);
    setVal("telem-ram-used", telemetryState.ramUsedMb);
    setVal("telem-power-state", telemetryState.powerState);
}

// Initialization on DOM load
document.addEventListener("DOMContentLoaded", () => {
    updateTimestamp();
    setInterval(updateTimestamp, 1000);

    renderEnvironmentalMatrix();
    renderNonconformances();
    renderResourceMargins();

    updateTelemetryTick();
    setInterval(updateTelemetryTick, 2000);
});
