# Failure Record: Restricted Sandbox Network

The initial full suite reported five failures in network/streaming tests because the restricted sandbox denied socket creation (`PermissionError: [Errno 1] Operation not permitted`). Re-running the same suite with host loopback access passed all five, producing the 340/340 baseline. A post-fix full-suite host rerun could not be requested after the environment usage-limit review; the post-fix targeted and camera-view suites passed.
