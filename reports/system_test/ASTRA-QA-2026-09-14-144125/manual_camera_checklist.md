# Manual Camera Acceptance Checklist

Operator result: **BLOCKED / PENDING**. The operator did not provide action-level confirmation during this campaign.

| Check | Result | Evidence / required operator observation |
|---|---|---|
| Camera, live video, person | PASS | Real frames and Mission Console capture; person observed by MediaPipe in 824 frames |
| 33-point pose and overlay | PASS (software/live observation) | 824 frames with 33 landmarks; `mission_console/running.png` |
| Hands and hand overlay | PASS (software/live observation) | 820 frames with hands; live overlay |
| MAIN_BOX / RED_BOX / YELLOW_BOX | BLOCKED | No operator object placement/action confirmation |
| Tracking, approach, reach, grasp, hold, move, place, release | BLOCKED | Physical procedure not performed/confirmed |
| Activity and four-step procedure | BLOCKED | No golden mission action trace |
| Wrong object, skipped step, incomplete action | PASS (automated only) / BLOCKED physical | Unit and regression tests; no physical injection |
| Recovery and recovery failure | PASS (automated only) / BLOCKED physical | Closed-loop unit tests; no physical corrective action |
| Voice | PASS software path; BLOCKED audible acceptance | voice events emitted; local audible confirmation unavailable |
| UI, recording, Ground Monitor | PASS observation | Screenshots, event telemetry, reconnect evidence |
