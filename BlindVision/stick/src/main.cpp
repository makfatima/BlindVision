// BlindVision Smart Stick - firmware entry point.
//
// Section III: "Core 0 of the ESP32 polls sensors at ~10-20 Hz and
// applies local safety logic; Core 1 manages the BLE stack and state
// machine. The stick continuously streams a structured sensor packet
// to the goggles over BLE."
//
// This firmware also implements Offline Stick Mode locally (Section
// III): if the goggles are unreachable, the stick still protects the
// user through its own haptics (vibrating faster as obstacles get
// closer, SOS flashing) using the same distance bands as Algorithm 1
// tiers 1-6, without R_vision.

#include <Arduino.h>

#include "ble_server.h"
#include "packet.h"
#include "pins.h"
#include "sensors.h"

namespace {

constexpr uint32_t SENSOR_POLL_HZ = 15;   // within the ~10-20 Hz range (Section III)
constexpr uint32_t SENSOR_POLL_PERIOD_MS = 1000 / SENSOR_POLL_HZ;

// Priority-tier distance bands, local subset (Table I / Algorithm 1
// tiers 1-6), used only for Offline Stick Mode haptics.
constexpr float CRITICAL_BAND_M = 0.5f;
constexpr float MEDIUM_BAND_M = 1.2f;
constexpr float LOW_BAND_M = 2.0f;

TaskHandle_t core0_task_handle = nullptr;
volatile uint32_t g_seq = 0;
SensorState g_latest_state{};
portMUX_TYPE g_state_mux = portMUX_INITIALIZER_UNLOCKED;

float nearest_horizontal_m(const SensorState &s) {
    float vals[4] = {s.front_m, s.left_m, s.right_m, s.rear_m};
    float best = NAN;
    for (float v : vals) {
        if (isnan(v)) continue;
        if (isnan(best) || v < best) best = v;
    }
    return best;
}

// Local haptic driver: continuous for critical, pulse rate increases
// as distance decreases otherwise. Runs whether or not the goggles are
// connected (Offline Stick Mode fallback, Section III).
void drive_local_haptics(const SensorState &s, bool sos_forced) {
    if (s.sos_pressed || sos_forced) {
        // Three distinct SOS pulses, reserved pattern (Section IV).
        for (int i = 0; i < 3; ++i) {
            digitalWrite(VIBRATION_MOTOR_PIN, HIGH);
            digitalWrite(LED_SAFETY_PIN, HIGH);
            delay(150);
            digitalWrite(VIBRATION_MOTOR_PIN, LOW);
            digitalWrite(LED_SAFETY_PIN, LOW);
            delay(150);
        }
        return;
    }

    if (s.ir_down_m > CRITICAL_BAND_M || nearest_horizontal_m(s) < CRITICAL_BAND_M || s.water_detected) {
        digitalWrite(VIBRATION_MOTOR_PIN, HIGH); // continuous
        return;
    }
    digitalWrite(VIBRATION_MOTOR_PIN, LOW);

    float nearest = nearest_horizontal_m(s);
    if (isnan(nearest)) return;

    // Pulse rate increases as distance decreases within medium/low bands.
    if (nearest < MEDIUM_BAND_M) {
        tone(BUZZER_PIN, 2000, 80);
    } else if (nearest < LOW_BAND_M) {
        tone(BUZZER_PIN, 1200, 60);
    }
}

// Core 0: sensor polling + local safety logic.
void core0_loop(void *) {
    sensors::begin();

    for (;;) {
        uint32_t cycle_start = millis();

        SensorState state = sensors::sample();
        bool forced_sos = sensors::fall_watchdog_tick(state.fall_detected);

        portENTER_CRITICAL(&g_state_mux);
        g_latest_state = state;
        portEXIT_CRITICAL(&g_state_mux);

        drive_local_haptics(state, forced_sos);

        uint32_t elapsed = millis() - cycle_start;
        if (elapsed < SENSOR_POLL_PERIOD_MS) {
            delay(SENSOR_POLL_PERIOD_MS - elapsed);
        }
    }
}

} // namespace

void setup() {
    Serial.begin(115200);
    Serial.println("[main] BlindVision Smart Stick booting...");

    ble_server::begin();

    // Pin Core 0 sensor task to CPU 0; loop()/Arduino runtime already
    // runs on CPU 1 alongside the BLE stack, matching the Section III
    // dual-core split.
    xTaskCreatePinnedToCore(core0_loop, "core0_sensors", 8192, nullptr, 1, &core0_task_handle, 0);
}

void loop() {
    // Core 1: BLE stack + state machine (streams the latest packet).
    SensorState state;
    portENTER_CRITICAL(&g_state_mux);
    state = g_latest_state;
    portEXIT_CRITICAL(&g_state_mux);

    StickPacket pkt = sensors::to_packet(state, g_seq++);
    ble_server::notify_packet(pkt);

    delay(50); // ~20 Hz packet stream, config/fusion_config.yaml [ble].expected_period_ms
}
