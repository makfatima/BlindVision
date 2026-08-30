# Proof-of-concept model status

## Status: NOT THE REPORTED FINE-TUNED MODEL

`proof_of_concept/cloud_server/app.py` currently instantiates the stock Ultralytics `yolov8n.pt` checkpoint. This is the cloud validation path described in the manuscript and is not the fine-tuned ten-class model reported for the main BlindVision evaluation.

The fine-tuned trained weights used for the reported results are not included in this release.
