# ASTRA-EA — Experiment Procedure Architecture

## 1. Overview & Core Architectural Principle

In autonomous spacecraft operations, high-level experiment milestones cannot simply be equated with raw computer vision activity concepts:

$$\text{Activity Concept} \neq \text{Experiment Step}$$

A physical activity such as `GRASP` or `MOVE` is a domain-agnostic physical action primitive. An experiment step (e.g., `STEP_02: Grasp Specimen Red Box`) is a context-dependent mission milestone governed by configured sequence rules, target objects, temporal intervals, and multimodal evidence requirements.

ASTRA-EA establishes a formal bridge between temporal activity observations and procedural step verification:

```mermaid
flowchart TD
    subgraph Perception_Tier [Perception Subsystem]
        Cam[Camera / Video] --> RawFrames[Raw Frame Packets]
        RawFrames --> PercState[PerceptionState (Tracks, Poses, Hands)]
    end

    subgraph Interaction_Tier [Interaction & Temporal Subsystem]
        PercState --> IntEvents[Spatial Interaction Events]
        IntEvents --> TempBuffer[Temporal Observation Buffer]
        TempBuffer --> ActObs[Activity Observation (Primitives / Composites)]
    end

    subgraph Procedure_Tier [Phase 4: Procedure Assurance Subsystem]
        ActObs --> ProcMatcher[Procedure Matcher (D4.01)]
        ProcMatcher --> StepCand[StepCandidate Hypotheses]
        
        ActObs & IntEvents & PercState --> EvEngine[Multimodal Evidence Engine (D4.02)]
        EvEngine --> EvBundle[Traceable EvidenceBundle]

        StepCand & EvBundle --> StepEval[Step Evaluator (D4.03)]
        StepEval --> EvalDecision[StepEvaluation (VERIFIED / UNCERTAIN / NOT_MATCHED)]

        EvalDecision --> ProgMgr[Procedure Progress Manager (D4.04)]
        ProgMgr --> NextEngine[Expected Next Step Engine (D4.05)]
    end

    subgraph Mission_Tier [Mission Database & Audit]
        StepEval --> SqliteEvals[(step_evaluations)]
        EvBundle --> SqliteBundles[(evidence_bundles)]
        ProgMgr --> SqliteProgress[(procedure_progress)]
    end
```

---

## 2. Component Directory & Subsystems

| Deliverable | Module | Purpose |
|---|---|---|
| **D4.01** | [`core/procedure/matcher.py`](file:///home/subish-loq/Documents/astra/core/procedure/matcher.py) | Maps activities to ranked step candidates based on action, object, and context |
| **D4.02** | [`core/evidence/engine.py`](file:///home/subish-loq/Documents/astra/core/evidence/engine.py) | Combines multimodal perception, kinematic, and spatial states into corroborating evidence |
| **D4.03** | [`core/procedure/evaluator.py`](file:///home/subish-loq/Documents/astra/core/procedure/evaluator.py) | Produces formal `StepEvaluation` decisions (`VERIFIED`, `UNCERTAIN`, `NOT_MATCHED`) |
| **D4.04** | [`core/procedure/progress.py`](file:///home/subish-loq/Documents/astra/core/procedure/progress.py) | Manages procedure lifecycle state machine, event deduplication, and completion |
| **D4.05** | [`core/procedure/next_step.py`](file:///home/subish-loq/Documents/astra/core/procedure/next_step.py) | Graph-based transition resolver supporting branches and optional steps |
| **D4.06** | [`core/evidence/engine.py`](file:///home/subish-loq/Documents/astra/core/evidence/engine.py) | Deterministic multi-factor evidence scoring formula |
| **D4.07** | [`core/procedure/traceability.py`](file:///home/subish-loq/Documents/astra/core/procedure/traceability.py) | Generates inspectable causal audit trees linking step decisions to raw frames |
| **D4.08** | [`core/procedure/visualizer.py`](file:///home/subish-loq/Documents/astra/core/procedure/visualizer.py) | Real-time developer step monitor overlay on video frames and terminal |
| **D4.11** | [`core/procedure/replay.py`](file:///home/subish-loq/Documents/astra/core/procedure/replay.py) | Offline deterministic replay of recorded event sequences |
| **D4.13** | [`core/mission/database.py`](file:///home/subish-loq/Documents/astra/core/mission/database.py) | SQLite audit tables for step evaluations, evidence bundles, and progress |
| **D4.15** | [`core/procedure/benchmark.py`](file:///home/subish-loq/Documents/astra/core/procedure/benchmark.py) | Empirical latency profiling across P50, P95, and P99 distributions |

---

## 3. Procedure State Machine

The procedure monitor adheres to a finite state machine:

```text
       ┌──────────┐
       │  READY   │
       └────┬─────┘
            │ Video input starts
       ┌────▼─────┐
       │MONITORING│◄─────────────────────────────┐
       └────┬─────┘                              │
            │ Activity observed                  │
       ┌────▼─────┐                              │
       │CANDIDATE │                              │
       └────┬─────┘                              │
            │ Evidence available                 │
       ┌────▼─────┐                              │
       │VERIFYING │                              │
       └────┬─────┘                              │
     ┌──────┴──────────────────┐                 │
     │                         │                 │
┌────▼─────┐             ┌─────▼─────┐           │
│ VERIFIED │             │ UNCERTAIN │───────────┘
└────┬─────┘             └───────────┘ (Requires more evidence;
     │ Step advanced                    does not advance silently)
┌────▼─────┐
│NEXT_STEP ├─────────────────────────┐
└────┬─────┘                         │
     │ All required steps satisfied  │
┌────▼─────┐                         │
│COMPLETED │◄────────────────────────┘
└──────────┘
```

### Critical Architectural Constraints:
1. **No Silent Advancement**: If an observed step candidate fails required evidence or duration checks, the state transitions to `UNCERTAIN`. The procedure remains at `current_step`.
2. **Event Deduplication**: Continuous execution of an ongoing activity generates multiple video frames but transitions the procedure exactly once unless `repeatable: true` is configured in the procedure schema.
3. **No Premature Deviation in Phase 4**: Candidate mismatches or out-of-order actions output `NOT_MATCHED` or `UNEXPECTED_CANDIDATE`. Final classification into `DEVIATION`, `SKIPPED_STEP`, `WRONG_OBJECT`, and vocal recovery guidance belongs exclusively to Phase 5.

---

## 4. Graph Transitions vs Linear Sequences

Universal spacecraft experiments cannot assume $next = current + 1$. The [`ExpectedNextStepEngine`](file:///home/subish-loq/Documents/astra/core/procedure/next_step.py) evaluates graph transitions defined in procedure YAML:

```yaml
transitions:
  STEP_01:
    next: ["STEP_02"]
  STEP_02:
    next: ["STEP_03"]
  STEP_03:
    next: ["STEP_04A", "STEP_04B"]
```

It also natively resolves:
* **Conditional Branching**: Validating runtime environment or result flags before selecting a branch.
* **Optional Steps**: When the immediate next step is marked `optional: true`, both the optional step and the subsequent step are valid next transitions.
* **Repeatable Steps**: When `repeatable: true`, the current step remains a valid re-entrant candidate.
