# BlindVision artifact status

This release contains the implementation and experimental/result artifacts described by the accompanying manuscript.

## Included

- Smart Goggles software
- Smart White Stick firmware
- sensor-fusion and arbitration implementation
- BLE communication components
- caregiver/backend components
- training/evaluation tooling and automated tests
- ten-class detection and classwise result tables
- per-tester navigation outcomes for the 100-trial aggregate (seven testers; see `data/raw/README.md` — this is not a breakdown by disability status)
- BLE and power measurements
- aggregate 20-session / 100-trial evaluation results
- the earlier ESP32-CAM/cloud YOLOv8n validation components

## Not included

Consistent with the manuscript's Data Availability statement, the complete image dataset and labels, the trained model weights used for the reported results, epoch-wise training logs, and raw confusion-matrix event data are not included in this release.

## Model status

The cloud-hosted YOLOv8n component is the earlier validation path described in the manuscript. Its stock checkpoint is not the fine-tuned ten-class model used for the reported main-system results.
