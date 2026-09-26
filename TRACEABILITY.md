# Traceability manifest

This file maps each result reported in the BlindVision manuscript to the repository artifact that supports it, and states what is not included.

| Reported result | Repository artifact |
|---|---|
| Ten-class dataset composition (Table S1) | `data/Dataset_Split.csv`, `data/Dataset_Manifest_.csv`, `data/Class_Definition.csv` |
| Held-out detection metrics (Table II) | `data/Heldout_Test.csv` |
| Ten-class confusion matrix (Table IV) | `data/Confusion_Matrix.csv` |
| Per-class counts, precision, recall | `data/Classwise_Evaluation.csv` (recomputed from `data/Confusion_Matrix.csv`) |
| Navigation outcomes (Table IX) | `data/raw/participant_trials_breakdown.csv`, `data/raw/participant_trial_outcomes_100.csv` (per-tester, see note below) |
| Full-system aggregate counts (Tables V, S2) | `data/Trial_Session__Summary.csv` |
| BLE results | `data/BLE_Trace__Summary.csv` |
| Power (Table X) | `data/Power_Log.csv` |
| Fusion/arbitration configuration (Algorithm 1) | `smart_goggles/config.py`, `smart_goggles/fusion/arbitration.py`, `data/Arbitration_Ladder_Supplied.csv` |
| Fused-score ceiling (Section IV) | `smart_goggles/fusion/risk_model.py` (`max_reachable_fused_score`), `tests/test_fusion_ceiling.py` |
| Caregiver event path | `backend/app.py`, `data/Caregiver_API_Runtime_Summary.csv` |
| Pending physical validations | `docs/PHYSICAL_TEST_PROTOCOLS.md`, `docs/RELEASE_CANDIDATE.md` |
| Consistency checks | `data/Consistency_Checks.csv` |

## Participant data

The `data/raw/` files break Table IX's 100-trial pool down by tester (P01-P07), not by visual status. The manuscript's seven visually impaired participants are a separate accounting (Section VI.A): one took part in trials inside this pool; six others completed a separate 48-trial session that is reported descriptively only and has no row-level file here.

## Detection accounting

`data/Confusion_Matrix.csv` is a matched class-to-class matrix: 842 ground-truth instances, 805 correct, 37 inter-class confusions. It has no background column; every ground-truth instance was matched to a prediction of some class. Table II's pooled precision combines the 37 confusions with 31 unmatched background false positives: 805 / 873 = 92.2%. Table III's 0.044 false positives per image uses the 31 background false positives alone. The per-class precision in `data/Classwise_Evaluation.csv` counts inter-class confusions only and is therefore higher than the pooled 92.2%.

Per-class AP values are not released, so mAP (Table II) cannot be recomputed from this repository.

## Timing, throughput, and power

- The 17.5 ms BLE value is a derived one-way estimate (RTT/2) from ping tokens timed on the Raspberry Pi; the devices share no clock.
- The 205 ms value is a serialized single-stream stage-sum (122 + 17.5 + 9 + 56 ms), not a direct end-to-end measurement.
- The 22.8 FPS four-camera figure was measured on earlier software, before the one-model-per-thread change. It is not a current-code benchmark; re-measurement is pending (`docs/PHYSICAL_TEST_PROTOCOLS.md`).
- `data/Power_Log.csv` holds five active-detection samples (mean 12.11 W). The ~3.1 h goggles runtime is a nominal-equivalent projection (37 Wh / 12.11 W), not a depletion test.

## Implementation status

- Vision distance is disabled while `CAMERA_FOCAL_LENGTH_PX` is `None` (the released default). The vision-proximity term and the vision clauses of Tiers 3, 8 and 9 are then inactive, and Tier 7 (HIGH_RISK_FUSED) is unreachable (ceiling ~0.608).
- Vision-Only Mode has a distance-independent fallback (Tier 9a, confidence >= 0.60), unit-tested in `tests/test_arbitration.py`; not yet physically fault-injection tested.
- The goggles-to-stick haptic write (`smart_goggles/ble/stick_link.py`, `send_haptic`) is unit-tested against a simulated BLE client (`tests/test_haptic_dispatch.py`); physical motor actuation is not yet tested.
- The proof-of-concept uses stock `yolov8n.pt`.

## Not included

Complete image/label dataset, trained weights for the primary results, epoch-wise training logs, per-class AP values, raw sequence-number BLE trace, and raw row-level prediction/event logs.
