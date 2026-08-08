# Contributing

## Ground rules

1. **The manuscript is the spec.** Any change to `config/fusion_config.yaml`,
   `goggles/fusion/fusion_engine.py`, `docs/fusion_algorithm.md`, or the
   BLE packet layout should be traceable to Section III/IV of the
   source manuscript, or clearly flagged in your PR description as a
   deliberate deviation/extension with your own rationale.
2. **`packet.h` and `packet.py` change together.** They define the same
   24-byte wire format from two sides of a BLE link. A PR that changes
   one without the other, and without a matching round-trip test in
   `goggles/tests/test_packet.py`, will not be merged.
3. **Every new fusion-tier behavior needs a test.** `goggles/tests/test_fusion_engine.py`
   is written to cover all ten tiers of Algorithm 1 individually, plus
   the manuscript's own worked example. Keep that property.

## Running tests locally

```bash
pip install -r goggles/requirements.txt -r backend/requirements.txt
pytest -v
```

## Firmware changes

`stick/` is a PlatformIO project. Build without hardware attached to
catch compile errors early:

```bash
cd stick && pio run -e esp32dev
```

## Style

- Python: standard library `dataclasses`/`enum` patterns already used
  throughout `goggles/`; keep new modules dependency-light and put
  hardware-only imports (`cv2`, `ultralytics`, `bleak`, `pyttsx3`)
  inside functions/try-except so the test suite keeps running without
  hardware or GPU drivers installed.
- C++: match the existing header/implementation split in `stick/include`
  and `stick/src`; keep `#pragma pack(push, 1)` on any wire-format struct.
