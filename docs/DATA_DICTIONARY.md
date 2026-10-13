# Data Dictionary: Pre-Submission Physical Tests

Protocol: `docs/PRE_SUBMISSION_PHYSICAL_TESTS.md`. Every row is a planned
trial. Fill only from real measurements; leave a cell empty if it was not
measured. Never back-fill from expected values.

Common columns: `session_id` (links to docs/EXPERIMENT_LOG.md, which records
date, operator, commit SHA, firmware build, environment), `evidence_ref`
(file name/ID of the video, photo or log in evidence/), `notes`.

## results/ultrasonic/ultrasonic_data_log.csv (1,800 rows)
- `matrix_type` — Directional (1,440), Downward (180), CrossTalk (180)
- `distance_cm` — target distance (Directional/CrossTalk) or sensor-to-ground reference height (Downward)
- `edge_state` — Flat or Dropoff_15cm (Downward only)
- `firing_mode` — Normal_all_five (released firmware), Solo_front_only (other four trigger wires disconnected), Concurrent_all_five
- `ground_truth_cm` — laser-meter (or tape, for downward) reference
- `measured_distance_cm` — value from the serial log; empty if no echo
- `no_echo` — 1 if timeout/0xFFFF, else 0
- `dropoff_flag` — Downward only: 1 if the firmware raised its drop-off flag, else 0
- `signed_error_cm`, `absolute_error_cm` — computed by analysis/analyze_physical_tests.py; do not type by hand

## results/vision_only/vision_only_trials_log.csv (80 rows, 20 per camera)
- `object_class_placed` — what was actually placed (person, chair, ...)
- `vision_only_mode_confirmed` — 1 if the goggles log showed vision_only before the block
- `actual_observed_warning` — exact spoken/logged text
- `confidence` — logged detector confidence
- `bearing_correct` — 1/0
- `latency_ms` — placement to speech onset, from video
- `outcome` — correct / wrong_bearing / wrong_class / no_warning

## results/haptic_sos/haptic_sos_trials_log.csv (30 rows)
- `video_fps` — slow-motion frame rate (e.g. 240)
- `frame_trigger` — Part A: obstacle placed; Part B: SOS button pressed
- `frame_haptic_onset`, `frame_speech_onset` — first visible motor movement / first audible speech
- `frame_speech_stop` — Part B: frame where the interrupted sentence stops
- `frame_sos_speech_onset` — Part B: first SOS speech
- `haptic_before_speech` (Part A), `speech_interrupted`, `sos_haptic_observed` (Part B) — 1/0
Times in ms are computed by the analysis script from frame differences and `video_fps`.
