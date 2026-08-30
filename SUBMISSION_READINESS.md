# Submission Readiness Checklist — BlindVision

## Manuscript/repository alignment

- [x] Full-system evaluation: 20 sessions and 100 navigation trials.
- [x] Participant-level record (`data/raw/`): per-tester breakdown (seven testers) of the same 100-trial pool, not a breakdown by disability status; the manuscript's seven-VI-participant cohort (Section VI.A) is distinct and only partially overlaps this pool (see `data/raw/README.md`).
- [x] Participant outcome totals reconcile to 96 successful and four unsuccessful outcomes.
- [x] Table IV and Table III use explicitly documented different accounting bases: 37 matched inter-class confusions in the closed matrix versus 31 unmatched/background false positives in the pooled detection accounting; see TRACEABILITY.md.
- [x] BLE result: 7920/8000 packets, 99.0%.
- [x] Ultrasonic result: 174/180, 96.7%.
- [x] SOS result: 20/20, 100%.
- [x] Water-hazard accuracy: 98.4%.
- [x] 205 ms is described as a single-stream processing-path estimate, not a direct four-camera timing measurement.
- [x] Four-camera throughput is reported as the measured 22.8 FPS aggregate.
- [x] Power provenance is aligned to the released five-sample active-detection log (12.11 W mean); unsupported idle/max-load runtime claims have been removed.
- [x] Smart Stick power domain is identified as 3.7 V nominal, 5000 mAh.
- [x] Goggles power domain is identified separately as the 10,000 mAh USB power bank.
- [x] Quantitative Vision-Only/Stick-Only/Fused ablation is not claimed because trial-level pairing is unavailable.
- [x] McNemar paired analysis is not claimed.
- [x] Missing trained weights and image/label dataset are not represented as included.
- [x] Future-work measurements are not presented as completed results.

## Final author/submission items

Before submission, the authors should still supply the final author list, affiliations, correspondence details, ORCID identifiers, and any venue-specific metadata required by the target IEEE venue.

- [x] BLE 17.5 ms is explicitly labeled as a derived RTT/2 one-way estimate.
- [x] Caregiver backend claims match the released local HTTP/API implementation; no smartphone app or Bearer authentication is claimed.
- [x] Remote goggles-to-stick haptic callback is disclosed as an integration stub.
- [x] Released vision distance estimation is disclosed as inactive until camera calibration is supplied.
