# BlindVision Release-Candidate Record

Branch: submission/v92-validation-freeze
Base main commit frozen for validation: 565580241b5c811bb18d1e786e24c251ce8b9b2c
Base commit date: 2026-09-23

## Validation state at freeze

The following software paths are present in the base commit:
- distance-independent Vision-Only warning fallback;
- one detector/model instance per camera thread;
- Raspberry-Pi-side BLE haptic write path;
- bearing-aware fusion implementation and reachability tests.

The following physical validations are not asserted as completed by this record:
- camera calibration and physical distance validation;
- reachable weighted-fusion experiment;
- Vision-Only fault-injection on assembled hardware using the corrected path;
- physical goggles-to-stick haptic actuation;
- current-code four-camera throughput benchmark;
- five-transducer ultrasonic array characterization;
- final held-out navigation evaluation after freezing all parameters.

See docs/PHYSICAL_TEST_PROTOCOLS.md.

## Claim-state rule
Do not move a result from implemented/software-tested to physically validated without a dated raw measurement linked to the release-candidate SHA.

## Repository integrity items
Before submission:
1. Resolve the DoorDetect redistribution/licensing status.
2. Release or otherwise make available the primary detector artifacts where legally permitted.
3. Ensure all manuscript-referenced protocol paths exist.
4. Record the final commit SHA in the manuscript.
5. Archive the final release immutably where possible.