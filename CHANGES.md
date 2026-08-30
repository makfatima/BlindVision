## Submission manuscript cleanup

- Removed the AI-Use Disclosure and its acknowledgement cross-reference from the submission manuscript.
- Added visible equation numbers to all four standalone formulas in the manuscript, with IEEE-style right-aligned numbering.
- Lightly tightened the contribution lead-in without changing experimental claims, measurements, or reported values.

## Confusion matrix update

- Added `data/Confusion_Matrix.csv` containing the supplied 10-class true-class/predicted-class matrix.
- Updated `data/Confusion_Event_Summary_.csv` to record the released aggregate matrix while keeping raw row-level prediction/event data excluded.

# BlindVision release changes

## Manuscript-aligned release

- Removed alternate datasets and analyses whose numerical scope or outcome definitions conflicted with the manuscript.
- Retained the seven-participant navigation summary and corresponding 100 trial-level participant outcome record with 96 successful and four partial-success outcomes.
- Removed paired ablation data and rule-level/sensitivity analyses identified by the manuscript as unavailable or future work.
- Removed incompatible runtime traces and model manifests describing a different accelerated/six-class configuration from the manuscript's reported main-system configuration.
- Removed stale repository copies and release metadata for superseded artifacts.
- Updated the numerical workbook README and removed workbook sheets corresponding to unavailable or future-work analyses.
- Rebuilt release metadata and SHA-256 checksums.

No missing trained weights, image/label records, epoch-wise training logs, or raw confusion-event observations were generated from manuscript summary values.

## Alignment-review fixes (post-confusion-matrix-update check)

- Corrected `README.md`, `PROVENANCE.md`, `SUBMISSION_READINESS.md`, `TRACEABILITY.md`, `ARTIFACT_STATUS.md`, `data/INDEX.csv`, `data/raw/README.md`, and `data/SUPPLIED_DATA_STATUS.md`/`data/RAW_DATA_RECONCILIATION.md`, which had mislabeled the seven-row `data/raw/participant_trials_breakdown.csv` (a per-tester breakdown of the manuscript's 100-trial navigation aggregate) as "seven visually impaired participants." Per Section VI.A, that 100-trial pool was run predominantly by sighted project-team members plus one VI participant; the manuscript's six additional VI participants ran a separate, descriptively-reported 48-trial batch with no row-level file in this release. No underlying data values were changed for this item — only the documentation labels.
- Renamed the stray `" artifacts_readme.md"` (leading space in the filename) to `data/artifacts_readme.md` and updated it and `data/README.csv` to mention `data/Confusion_Matrix.csv`.
- Regenerated `data/Classwise_Evaluation.csv` directly from `data/Confusion_Matrix.csv` (TP = diagonal, FP = column sum − diagonal, FN = row sum − diagonal) so the two per-class files agree with each other; mAP@0.5/mAP@0.5:0.95 columns are retained from the prior release since mAP cannot be recomputed from a confusion matrix alone.
- Applied the same `Classwise_Evaluation` correction to the `Classwise_Evaluation` sheet inside `data/BlindVision__dataset (1).xlsx`, which still held the pre-confusion-matrix per-class numbers, and updated that workbook's README sheet, which described the old "839 class-assigned + 3 unmatched" accounting no longer used by the new Table IV.
- **Flagged, not silently fixed:** the confusion-matrix update introduced a new discrepancy — its off-diagonal mass gives a 37-total false-positive count across classes, which does not match Table III's separately reported 31 false positives / 700 images (used in Table II's 96.3% precision figure). A closed 10×10 confusion matrix with no background/no-detection bucket cannot produce FP ≠ FN, so this needs an authors' decision on which framework is correct or how to reconcile them; see `TRACEABILITY.md` for the full explanation.
- Replaced the stale copy of the manuscript at `docs/BlindVision_FINAL_MANUSCRIPT.docx` with the corrected, combined version (main text + regenerated Figures 1–4 + Supplementary Material Tables S1–S7 merged into one file).
- Regenerated Figures 1–4 in the manuscript, which had drifted from the body text and the fusion code: Fig. 1 said "BLE 5.0" (text/code: BLE 4.2) and labelled the backend link "TLS/AES-256" (text: TLS 1.2 for the backend link, AES-CCM for the BLE link); Fig. 2 labelled the BLE hop "~58 ms" (measured: 17.5 ms) and showed the fusion engine as `R = max(R_stick, R_vision)`; Fig. 3 additionally mislabeled the fusion step "Feature-level fusion" (the paper is explicit that this is score-level fusion) with the same incorrect `max()` formula; Fig. 4 showed a 0.50 confidence threshold (text/Table II: 0.45). All four now show `R = 0.40C + 0.20P + 0.25U + 0.15W`, matching Section IV and `smart_goggles/fusion/risk_model.py`.
## Final repository synchronization

- Replaced `docs/BlindVision_FINAL_MANUSCRIPT.docx` with the current canonical manuscript supplied for submission.
- Removed the duplicated reflective-surface sentence/paragraph in the failure-mode analysis.
- Hardened `tools/verify_artifacts.py` so an incorrectly supplied non-YAML `--data` path produces a clear validation message instead of an AttributeError.
- Rebuilt repository SHA-256 metadata after the synchronization.
