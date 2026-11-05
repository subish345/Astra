# ASTRA-EA System Validation Campaign

Run ID: `ASTRA-QA-2026-09-14-144125`  
Scope: ASTRA-EA 6 complete system QA, debugging, regression, live camera and release readiness.

This campaign preserves the pre-campaign dirty tree in `working_tree_before.patch`, records every command in `commands.jsonl`, and keeps artifacts isolated under this timestamped directory. Physical action acceptance requires operator confirmation and is therefore marked blocked below.

Evidence map: `automated/` contains command logs and JUnit XML; `camera/` contains real camera timestamps and observer video; `perception/` contains live overlays and sampled state; `mission_console/` contains UI captures and event telemetry; `performance/` contains measured latency, throughput and soak data; `regression/` contains regression JUnit XML.
