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
## Post-freeze implementation changes (28 Sep 2026 audit response)
These change implementation code after the base commit above, so the new
release commit is NOT code-identical to the freeze. Record its SHA here and in
the manuscript once pushed: `<NEW_COMMIT_SHA>`.

1. `smart_goggles/audio/tts_engine.py` — the remote haptic command is sent
   before speech (previously after the full utterance); SOS sends its haptic
   immediately and interrupts an utterance already in progress at the next
   word boundary. Tests: `tests/test_dispatch_order.py` (fake engine).
   Not yet verified on the Pi's speech engine or physically measured.
2. `smart_goggles/config.py`, `smart_goggles/camera/detector.py` — per-camera
   focal length (`CAMERA_FOCAL_LENGTH_PX_BY_BEARING`) and a
   `VISION_DISTANCE_VALIDATED` gate (default False): populating a focal length
   alone no longer activates vision distance. Released behaviour is unchanged
   (distance disabled). Tests: `tests/test_vision_distance_gate.py`.
   Lens-distortion correction is still not implemented.

Physical validation for item 1 should record decision-to-BLE-write, stick
receipt, motor onset, speech onset, and SOS pre-emption while another alert is
being spoken.
