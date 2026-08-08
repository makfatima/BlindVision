# Hardware Bring-Up: Verifying the Smart Stick's Wiring

`stick/include/pins.h` is a reference pin assignment. It has not been
verified against a specific physical board in this repository — there
is no hardware attached to this development environment to check it
against. What *is* provided is a fast, repeatable way for you to
verify it against your own board before trusting the main firmware's
sensor fusion output.

## Run the self-test firmware first

```bash
cd stick
pio run -e esp32dev_selftest -t upload -t monitor
```

This builds `stick/src/selftest/selftest_main.cpp` instead of the main
application (`platformio.ini` defines `esp32dev_selftest` as a separate
environment with its own `build_src_filter`, so `main.cpp` and
`ble_server.cpp` are excluded from this build — no BLE, no fusion
logic, just raw sensor I/O).

Once flashed, the serial monitor prints, once per second:

```
--------------------------------------------------
front=  1.20m  left=  0.85m  right=  2.40m  rear=  3.00m  down=  0.31m
ir_down=  0.28m  water=0  fall=0  sos=0  calibrated=1  battery=87%
[selftest] Testing VIBRATION_MOTOR_PIN...
[selftest] Testing BUZZER_PIN...
[selftest] Testing LED_SAFETY_PIN...
```

## What to check

1. **Ultrasonic sensors** (`front`/`left`/`right`/`rear`/`down`): wave
   a hand in front of each physical sensor in turn and confirm the
   *matching* field in the printout changes. If `front` doesn't
   respond but `left` does when you wave in front of the front sensor,
   the `US_FRONT_TRIG`/`US_FRONT_ECHO` pins in `pins.h` are likely
   swapped with another sensor's.
2. **Stuck-at-zero or always-out-of-range readings**: the tool prints
   an inline `WARNING` for these automatically — usually a trig/echo
   swap, a bad ground connection, or insufficient 5V supply to that
   sensor rather than a real "no obstacle" reading.
3. **IR sensors** (`ir_down`): cover/uncover the downward IR sensor(s)
   and confirm the value changes plausibly. Don't trust the absolute
   meters value yet — that depends on `docs/calibration.md` §2, not
   just wiring.
4. **Water sensor**: dip the tip in water (or touch the two probes
   with a wet finger) and confirm `water` flips from `0` to `1`.
5. **IMU**: gently tap or shake the stick and confirm `fall` flips to
   `1` momentarily. If it's always `0` even when you shake it firmly,
   check `IMU_SDA_PIN`/`IMU_SCL_PIN` wiring and the I2C address
   (`IMU_I2C_ADDR`) in `pins.h`.
6. **FSR**: press the tip against a hard surface and confirm
   `calibrated` (ground-contact proxy) flips to `1`.
7. **SOS button**: press it and confirm `sos` flips to `1`. It's wired
   active-low with an internal pull-up in this reference assignment —
   if it reads `1` when *not* pressed, either the pull-up isn't
   engaging or the button is wired to the wrong logic level.
8. **Outputs**: during the `[selftest] Testing ...` lines, confirm the
   vibration motor actually vibrates, the buzzer actually beeps, and
   the LED actually lights, each only during its own 500ms window.

## After wiring checks out

1. Run through `docs/calibration.md` for the IR sensor and vision
   distance curves — a self-test pass confirms wiring, not that the
   *distance numbers* are accurate.
2. Flash the main firmware: `pio run -e esp32dev -t upload`.
3. Pair the Smart Goggles and confirm packets arrive — see
   `docs/ble_protocol.md`.

## If your physical pin-out differs from `pins.h`

Just edit `stick/include/pins.h` directly — every other file
(`sensors.cpp`, `ble_server.cpp`, `main.cpp`,
`selftest/selftest_main.cpp`) references pins only through the named
constants in that one file, so a wiring change never requires touching
sensor logic.
