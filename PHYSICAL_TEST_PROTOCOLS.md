# BlindVision — Physical Test Protocols
Everything solvable from the repo/code/manuscript has been done below. What's left in
each section is only what genuinely requires the assembled hardware in front of you.

---

## 1. Vision-Only Mode fault-injection retest — **Category C**

**What triggers it (confirmed from code, `smart_goggles/fusion/arbitration.py`):**
When the stick link times out (no packet for `STICK_LINK_TIMEOUT_S` = 5 s), the system
enters `vision_only` mode. If the camera is uncalibrated (`config.CAMERA_FOCAL_LENGTH_PX`
is `None`, the shipped default), every detection has `distance_m = None`. The new
`VISION_WARNING_UNCALIBRATED` tier fires when: mode is `vision_only`, no detection has a
distance, AND the highest-confidence detection's confidence ≥
`VISION_ONLY_WARNING_CONFIDENCE_MIN` (0.60). It announces class + bearing, no distance.

**Procedure:**
1. Power on both devices, let them pair normally (Normal Mode).
2. Place one clearly-recognizable object (e.g. a chair) in view of one camera, confidence
   should read comfortably above 0.60 in the console log.
3. Power off the Smart Stick (or physically disconnect it).
4. Wait 6+ seconds (past the 5 s timeout).
5. Confirm in the console log that mode has switched to Vision-Only.
6. Confirm you hear a spoken alert naming the object and its bearing (no distance
   mentioned).
7. Remove the object from view; confirm alerts stop (system returns to no-alert/ROUTINE
   state without the object).
8. Reconnect the stick; confirm the system returns to Normal Mode and stick-driven
   alerts (e.g. SOS button) work again.

**Fill in and send back:**

| Step | Expected | Observed | Pass/Fail |
|---|---|---|---|
| 3-5 | Mode switches to Vision-Only within ~5-6s of stick disconnect | | |
| 6 | Spoken alert names object class + bearing, no distance figure | | |
| 7 | Alert stops when object removed | | |
| 8 | Reconnecting stick restores Normal Mode | | |

**Manuscript wording:** already correct — Section III states the fallback is "unit-test
coverage... has not yet been re-validated by physical fault-injection testing." Once you
send results, that sentence gets updated to state the retest was performed, with the
actual outcome (pass, or whatever it actually showed).

---

## 2. Four-camera FPS re-measurement — **Category B** (script ready, you run it)

**Confirmed from code:** each of the 4 `_camera_worker` threads now builds its own
`YoloDetector`/model instance (`smart_goggles/main.py`) — the shared-instance race this
number needed re-measuring for is fixed.

**What to measure:** the same metric as before (so the numbers are comparable) — frames
processed per camera stream over a fixed wall-clock window, all 4 cameras running
concurrently.

**Exact command** (the repo already has the harness that produced the original number
— it already reports aggregate and per-camera throughput as part of its normal output,
so no new script is needed):
```bash
cd smart_goggles/instrumentation
python3 bench_latency.py --reps 100 --out runs/throughput_retest.csv
python3 summarize.py runs/throughput_retest.csv --ieee
```
`--reps 100` matches the repetition count the original measurement protocol used per
camera direction; the run continues until every bearing has reached it. This is the
same tool, same invocation shape, that produced the original 22.8/5.7 FPS figures — not
a new script I'm asking you to build.

**Record whatever `summarize.py --ieee` prints for throughput** (paste-ready rows per its
own docstring) — at minimum:

| Metric | Old (pre-fix) | New (fill in) |
|---|---|---|
| Aggregate FPS (4 cameras) | 22.8 | |
| Per-camera mean FPS | 5.7 | |
| Per-camera frame counts (if reported) | not logged | |
| Dropped-frame rate under 4-stream load | not reported | |

**Every place the old 22.8/5.7 FPS numbers currently appear** (all already flagged as
requiring re-validation, not deleted): Abstract, Conclusion, Section V.D (repo note),
Section VI.I (main throughput report), Section VI.K item 8 (threats to validity), Table
XI, the Strengths bullet in Discussion. Once you send the new number, I'll replace all of
these in one pass — I won't leave some updated and others stale.

**Do not** run this on a single camera and multiply by 4 — that's exactly the naive
projection the manuscript already explains is ~30% higher than reality; the whole point
is measuring real contention.

---

## 3. Haptic motor validation — **Category C**

**Path confirmed complete in software** (`smart_goggles/audio/tts_engine.py` →
`smart_goggles/ble/stick_link.py`'s `send_haptic` → `smart_stick/ble_peripheral.cpp`'s
`RxCallbacks::onWrite` → `smart_stick/smart_stick.ino`'s `onHapticCommand` →
`outputs_set_pattern`). Unit tests (`tests/test_haptic_dispatch.py`) confirm the software
logic; nothing confirms the physical motor moves.

**Procedure:**
1. Power on both devices, confirm BLE connection (Normal Mode).
2. Trigger a fused alert that should produce a haptic pattern — easiest is a
   `CRITICAL_OBSTACLE` (put a person/vehicle-class object within 2 m of the camera, or
   bring the stick's front ultrasonic below 0.5 m).
3. Watch/feel the stick's vibration motor. Note whether it activates, and roughly what
   pattern (continuous vs. pulsing).
4. Repeat for at least one more tier — e.g. `MEDIUM` (single pulse) — to confirm
   different patterns are distinguishable, not just "does it buzz at all."
5. Separately, trigger a stick-local hazard (e.g. lift the stick off the ground to
   simulate a drop-off) with the goggles link disconnected, and confirm the stick's
   *local* haptic loop still works — this path was already validated in earlier rounds
   and this step just confirms nothing broke.

**Fill in and send back:**

| Trigger | Expected pattern | Motor activated? (Y/N) | Pattern matched? (Y/N) |
|---|---|---|---|
| CRITICAL_OBSTACLE (vision or stick) | continuous | | |
| MEDIUM | single pulse | | |
| Stick-local drop-off (goggles disconnected) | continuous, stick-only | | |

**Three-way distinction to keep in the manuscript** (already present, will be updated
once you send results): implemented (yes) → unit-tested (yes, `test_haptic_dispatch.py`)
→ physically validated (pending — this table).

---

## 4. Per-transducer ultrasonic characterization — **Category C**

**Is this required for existing claims, or a limitations item?** Limitations — Table VII's
existing 96%-accuracy figure came from **one** transducer at 18 reference points; nothing
in the current results depends on this new data. This is closing a disclosed gap, not
correcting a wrong claim.

**Minimum useful design** (small enough to actually finish in an afternoon):

*Hardware setup:* stick mounted on a fixed stand at a consistent height; a flat target
board you can position at exact distances/angles; a tape measure.

**A. Distance accuracy per transducer** (extends Table VII's single-transducer test to
all 5)
- Independent variable: true distance (tape-measured)
- Controlled: room temperature, target = flat cardboard (matches Table VII's original
  material), target directly ahead of the transducer (0° incidence)
- Test distances: 30, 60, 100, 150, 200, 250 cm (6 points — fewer than the original 18,
  enough to catch a systematically-off transducer)
- Repetitions: 5 per distance per transducer (down from the original 10 — still enough
  for a mean/SD)
- Record: `transducer, true_distance_cm, reading_1..5_cm, mean, SD`

**B. Angle of incidence** (one transducer, e.g. front, is enough — the question is
whether the *principle* holds, not all 5 independently)
- Fixed distance: 100 cm
- Angles: 0°, 15°, 30°, 45° off-perpendicular
- Repetitions: 5 per angle
- Record: `angle_deg, reading_1..5_cm, mean, SD, dropout_count` (dropout = no echo
  returned at all)

**C. Target material** (front transducer, 100 cm, 0°)
- Materials: cardboard (baseline), glass/mirror, dark cloth/fabric, bare skin (hand held
  flat) — these are the four surfaces most likely in real navigation (wall, window,
  clothing, a person)
- Repetitions: 5 per material
- Record: `material, reading_1..5_cm, mean, SD, dropout_count`

**D. Cross-talk** (the one that needs two transducers active)
- Fire front and rear simultaneously (both aimed at target boards at a known distance,
  e.g. 100 cm each) for 20 cycles; record whether either transducer's reading is
  corrupted (wildly wrong value or dropout) compared to its solo-firing baseline from
  test A
- Record: `cycle, front_reading, rear_reading, front_corrupted(Y/N), rear_corrupted(Y/N)`

**Acceptance/interpretation:** no pass/fail threshold needed — this is a
characterization, not a validation gate. Report mean ± SD per condition; flag any
transducer/angle/material combination with >10% dropout rate or >15% mean error as
worth a sentence of caveat in the manuscript.

---

## 5. Fusion weight/threshold sensitivity sweep — **Category A, done now**

Re-verified directly against the current code (`smart_goggles/fusion/risk_model.py`,
`smart_goggles/config.py`):

- Current weights: `w_vc=0.40, w_vp=0.20, w_sp=0.25, w_sc=0.15`
- `HIGH_RISK_FUSED_THRESHOLD = 0.80`
- **Confirmed still true:** ceiling = **0.6083** under the current uncalibrated
  configuration (below threshold — unreachable), and **0.8083** if the camera were
  calibrated (above threshold — reachable). Unchanged from the last check; this is
  computed by `max_reachable_fused_score()`, not hand-derived, and pinned by
  `tests/test_fusion_ceiling.py`.

**Can an actual sensitivity sweep run on existing data?** No — a sweep needs the 100
navigation trials' underlying per-trial sensor readings (what detection/distance/stick
values fed the fusion score at the moment of each trial), re-run through the arbitration
logic at ±20% weight perturbations, to see whether the same tier still fires. The
released `data/` only has trial *outcomes* (pass/fail), not the per-trial raw sensor
inputs — so there's nothing to replay the sweep against. This isn't a gap I can close by
analysis; it needs either new trials run with raw-input logging enabled, or the original
raw logs if they still exist somewhere (check your own machine/Pi SD card/Colab history —
if you have the original per-trial JSON/CSV inputs, send them and I can run the sweep
computationally with no new hardware time needed).

**If you do have to collect new data:** minimum viable version is running each of the
current 100-trial's five scenarios (Section VI.F) once more at 4 perturbed weight sets
(+20%/−20% on `w_vc` alone, then on `w_sp` alone, holding the others at nominal) and
recording which tier fired each time — a 20-trial mini-study, not a full 500-trial redo.

---

## 6. Paired subsystem ablation — **Category C, confirmed not computable from existing data**

Checked `data/raw/participant_trial_outcomes_100.csv` directly: columns are
`Trial_ID, Participant, Outcome` — no configuration column, no pairing ID. Every trial in
that file is the **Fused** configuration; there is no Vision-Only-only or Stick-Only-only
trial-level record anywhere in the released data. This matches what the manuscript
already says (Table X) — confirmed again, not newly found, but ruled out as
newly-computable from existing files.

**Smallest paired design:** re-run a subset of the existing five navigation scenarios
(Section VI.F) — say 10 trials per scenario, 50 total — three times each: Vision-Only,
Stick-Only, Fused, same route/obstacle placement each time, same success definition
already used for Table IX (no collision, correct guidance issued, route completed).

**Table to fill in per trial:**

| Trial # | Scenario | Configuration | Success (Y/N) | Notes |
|---|---|---|---|---|
| 1 | Corridor | Vision-Only | | |
| 1 | Corridor | Stick-Only | | |
| 1 | Corridor | Fused | | |
| ... | | | | |

Once filled, McNemar's test on the Fused-vs-Vision-Only and Fused-vs-Stick-Only
discordant pairs is the right analysis (paired binary outcomes, same trial) — I can run
that the moment you send the filled table; no need to compute it by hand.

---

## 7. Stick continuous-discharge test — **Category C**

**From code/hardware docs:** 3.7 V, 5000 mAh 18650 Li-ion cell, TP4056 charger
(`smart_stick/config.h`). No existing stick-side discharge data anywhere in the repo (only
the goggles' 5 V bus is logged in `Power_Log.csv`).

**Procedure:**
1. Fully charge the stick (TP4056 LED confirms full charge).
2. Configuration: stick running normally (sensors polling at the standard rate,
   BLE connected to goggles, no artificial idle/sleep mode) — i.e. the same "active"
   state the goggles' power log already characterizes, so the two are comparable.
3. Measure and log voltage every 15 minutes with a multimeter across the battery
   terminals (or an inline USB/battery power meter if you have one — more precise, less
   manual).
4. Stopping condition: either the stick's own low-battery cutoff engages, or voltage
   drops to 3.0 V (typical 18650 safe discharge floor) — whichever comes first. Do not
   run past 3.0 V; over-discharging a Li-ion cell degrades or damages it.
5. Safety: do this somewhere you can watch it (Li-ion cells can vent/swell if something
   is wired wrong) — not unattended overnight for the first run.

**Table:**

| Time (min) | Voltage (V) | Notes |
|---|---|---|
| 0 | | fully charged |
| 15 | | |
| 30 | | |
| ... | | |
| stop | | cutoff reason |

**What this replaces:** the manuscript's current "≈8.7 h derived upper bound, no
continuous discharge test run" (from nominal 5000 mAh / 575 mA assumed draw) becomes a
measured runtime once you send this table — I'll compute actual mAh consumed
(capacity × (1 − remaining-voltage-fraction), or more precisely by integrating measured
current if you used a power meter) and replace the derived figure with the measured one.

---

## Summary classification

| # | Item | Category | What's done now | What you do |
|---|---|---|---|---|
| 1 | Vision-Only retest | C | Trigger condition confirmed, protocol + table ready | Run steps, fill table |
| 2 | FPS re-measurement | B | Script/command identified, every affected manuscript location listed | Run command, send numbers |
| 3 | Haptic validation | C | Full path traced, protocol + table ready | Run steps, fill table |
| 4 | Ultrasonic characterization | C | Full 4-part design (distance/angle/material/cross-talk), tables ready | Run experiments, fill tables |
| 5 | Fusion sensitivity sweep | **A** | Ceiling re-verified (0.608/0.808); confirmed no existing raw per-trial data to sweep against | Only needed if you want it done — send raw logs if they exist, or run the 20-trial mini-study |
| 6 | Paired ablation | C | Confirmed existing data can't answer this; minimal 50-trial design + table ready | Run trials, fill table, send back — I'll run McNemar |
| 7 | Stick discharge | C | Protocol + table ready | Run test, fill table |
