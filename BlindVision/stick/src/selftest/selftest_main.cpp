// BlindVision Smart Stick - hardware self-test mode.
//
// Build with `pio run -e esp32dev_selftest -t upload` (see
// platformio.ini) instead of the main firmware to verify your physical
// wiring matches include/pins.h *before* trusting main.cpp's sensor
// fusion output. This cannot be verified without a physical board —
// this file exists to make that verification fast and repeatable once
// you have one.
//
// Protocol (over Serial @ 115200):
//   - Prints live readings for every sensor once per second.
//   - Cycles each output (vibration motor, buzzer, LED) for 500ms in
//     turn, announcing which one is active, so you can visually/aurally
//     confirm each pin drives the physical device you expect.
//   - Prints a WARNING for any sensor reading that looks implausible
//     (e.g. an ultrasonic reading stuck at 0 or always at max range),
//     which usually means a wiring or power problem rather than a real
//     "no obstacle" reading.

#include <Arduino.h>
#include <Wire.h>

#include "pins.h"
#include "sensors.h"

namespace {

constexpr uint32_t OUTPUT_STEP_MS = 500;

void announce(const char *label) {
    Serial.print("[selftest] ");
    Serial.println(label);
}

void test_outputs_once() {
    announce("Testing VIBRATION_MOTOR_PIN...");
    digitalWrite(VIBRATION_MOTOR_PIN, HIGH);
    delay(OUTPUT_STEP_MS);
    digitalWrite(VIBRATION_MOTOR_PIN, LOW);

    announce("Testing BUZZER_PIN...");
    tone(BUZZER_PIN, 2000);
    delay(OUTPUT_STEP_MS);
    noTone(BUZZER_PIN);

    announce("Testing LED_SAFETY_PIN...");
    digitalWrite(LED_SAFETY_PIN, HIGH);
    delay(OUTPUT_STEP_MS);
    digitalWrite(LED_SAFETY_PIN, LOW);
}

void print_sensor_snapshot(const SensorState &s) {
    Serial.println("--------------------------------------------------");
    Serial.printf("front=%6.2fm  left=%6.2fm  right=%6.2fm  rear=%6.2fm  down=%6.2fm\n",
                   s.front_m, s.left_m, s.right_m, s.rear_m, s.down_m);
    Serial.printf("ir_down=%6.2fm  water=%d  fall=%d  sos=%d  calibrated=%d  battery=%d%%\n",
                   s.ir_down_m, s.water_detected, s.fall_detected, s.sos_pressed,
                   s.calibrated, s.battery_pct);

    // Sanity checks: a sensor stuck at 0 or always NAN/out-of-range
    // across many samples usually indicates a wiring fault, not a real
    // reading. This tool prints an in-line warning; it does not try to
    // auto-diagnose which wire is wrong.
    auto check = [](const char *name, float m) {
        if (isnan(m)) {
            Serial.printf("  WARNING: %s reads out-of-range on every sample so far -- "
                          "check trig/echo wiring and 5V supply.\n", name);
        } else if (m < 0.02f) {
            Serial.printf("  WARNING: %s reads ~0m -- check for a short or a sensor "
                          "pressed against a surface.\n", name);
        }
    };
    check("front", s.front_m);
    check("left", s.left_m);
    check("right", s.right_m);
    check("rear", s.rear_m);
    check("down", s.down_m);
}

} // namespace

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n=== BlindVision Smart Stick hardware self-test ===");
    Serial.println("Cross-check every reading below against include/pins.h and your");
    Serial.println("physical wiring. Ctrl+C / close the monitor to stop.\n");

    pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_SAFETY_PIN, OUTPUT);

    sensors::begin();
}

void loop() {
    SensorState s = sensors::sample();
    print_sensor_snapshot(s);
    test_outputs_once();
    delay(1000);
}
