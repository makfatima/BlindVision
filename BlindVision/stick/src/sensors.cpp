// BlindVision Smart Stick - sensor sampling implementation.
// See include/sensors.h for the public interface and design rationale.

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>   // register-compatible base driver for MPU9250 accel/gyro
#include <Adafruit_Sensor.h>

#include "pins.h"
#include "sensors.h"

namespace {

Adafruit_MPU6050 imu;

// Ground-plane / calibration constants (Section IV / config/fusion_config.yaml)
constexpr float DROPOFF_THRESHOLD_M = 0.5f;
constexpr float FALL_ACCEL_SPIKE_G = 2.5f;       // |a| spike consistent with a fall
constexpr uint32_t FALL_WATCHDOG_NO_RECOVERY_MS = 8000; // Section IV config

constexpr float ULTRASONIC_TIMEOUT_US = 30000.0f; // ~5m round-trip ceiling
constexpr float SOUND_SPEED_M_PER_US = 0.000343f;  // m per microsecond, /2 for round trip

uint32_t fall_detected_at_ms = 0;
bool fall_watchdog_armed = false;

float read_ultrasonic_m(int trig_pin, int echo_pin) {
    digitalWrite(trig_pin, LOW);
    delayMicroseconds(2);
    digitalWrite(trig_pin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trig_pin, LOW);

    unsigned long duration_us = pulseIn(echo_pin, HIGH, ULTRASONIC_TIMEOUT_US);
    if (duration_us == 0) {
        return NAN; // out of range / no echo
    }
    return duration_us * SOUND_SPEED_M_PER_US / 2.0f;
}

// Sharp GP2Y0A21YK0F-style analog IR: distance_cm = A * V^B, where V is
// the sensor's analog output voltage (NOT the raw ADC count -- the ADC
// count depends on your board's ADC resolution/reference voltage and
// must be converted to volts first). A=27.86, B=-1.15 are the commonly
// cited datasheet-fit constants for this sensor family; they are a
// reasonable *starting point*, not a substitute for calibrating your
// specific sensor unit. Recalibrate with tools/calibrate_ir_sensor.py
// (take several (adc_raw, known_distance_cm) samples, fit, and paste
// the resulting A/B here) and update these two constants.
constexpr float IR_CALIB_A = 27.86f;
constexpr float IR_CALIB_B = -1.15f;
constexpr float ADC_MAX_COUNT = 4095.0f;   // 12-bit ADC
constexpr float ADC_REF_VOLTAGE = 3.3f;
constexpr int IR_SATURATION_RAW = 50;       // below this, treat as out-of-range

float read_ir_down_m(int pin) {
    int raw = analogRead(pin);
    if (raw < IR_SATURATION_RAW) return NAN; // saturated / out of range
    float voltage = (raw / ADC_MAX_COUNT) * ADC_REF_VOLTAGE;
    float distance_cm = IR_CALIB_A * powf(voltage, IR_CALIB_B);
    return distance_cm / 100.0f; // -> meters
}

bool read_water_detected() {
    int raw = analogRead(WATER_SENSOR_PIN);
    return raw > 1500; // resistive sensor: higher reading => moisture present
}

bool read_fsr_ground_contact() {
    int raw = analogRead(FSR_PIN);
    return raw > 200; // tip is touching the ground
}

uint8_t read_battery_pct() {
    int raw = analogRead(BATTERY_ADC_PIN);
    // 3.0V (0%) - 4.2V (100%) across a resistor divider tuned to the ADC range.
    float voltage = (raw / 4095.0f) * 3.3f * 2.0f; // divider ratio 2:1
    float pct = (voltage - 3.0f) / (4.2f - 3.0f) * 100.0f;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return static_cast<uint8_t>(pct);
}

bool detect_fall() {
    sensors_event_t a, g, temp;
    imu.getEvent(&a, &g, &temp);
    float mag_g = sqrtf(a.acceleration.x * a.acceleration.x +
                         a.acceleration.y * a.acceleration.y +
                         a.acceleration.z * a.acceleration.z) / 9.80665f;
    return mag_g > FALL_ACCEL_SPIKE_G;
}

} // namespace

namespace sensors {

void begin() {
    pinMode(US_FRONT_TRIG, OUTPUT); pinMode(US_FRONT_ECHO, INPUT);
    pinMode(US_LEFT_TRIG, OUTPUT);  pinMode(US_LEFT_ECHO, INPUT);
    pinMode(US_RIGHT_TRIG, OUTPUT); pinMode(US_RIGHT_ECHO, INPUT);
    pinMode(US_REAR_TRIG, OUTPUT);  pinMode(US_REAR_ECHO, INPUT);
    pinMode(US_DOWN_TRIG, OUTPUT);  pinMode(US_DOWN_ECHO, INPUT);

    pinMode(SOS_BUTTON_PIN, INPUT_PULLUP);
    pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_SAFETY_PIN, OUTPUT);

    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
    if (!imu.begin(IMU_I2C_ADDR)) {
        Serial.println("[sensors] WARNING: IMU not detected; fall detection degraded.");
    }
}

SensorState sample() {
    SensorState s{};

    s.front_m = read_ultrasonic_m(US_FRONT_TRIG, US_FRONT_ECHO);
    s.left_m  = read_ultrasonic_m(US_LEFT_TRIG, US_LEFT_ECHO);
    s.right_m = read_ultrasonic_m(US_RIGHT_TRIG, US_RIGHT_ECHO);
    s.rear_m  = read_ultrasonic_m(US_REAR_TRIG, US_REAR_ECHO);
    s.down_m  = read_ultrasonic_m(US_DOWN_TRIG, US_DOWN_ECHO);

    // Drop-off: downward IR reports no ground return closer than 0.5m,
    // i.e. measured down-distance exceeds the nominal ground plane (Section IV).
    float ir1 = read_ir_down_m(IR_DOWN_1_PIN);
    float ir2 = read_ir_down_m(IR_DOWN_2_PIN);
    s.ir_down_m = isnan(ir1) ? ir2 : (isnan(ir2) ? ir1 : min(ir1, ir2));

    s.water_detected = read_water_detected();
    s.fall_detected = detect_fall();
    s.sos_pressed = (digitalRead(SOS_BUTTON_PIN) == LOW); // active-low
    s.calibrated = read_fsr_ground_contact(); // proxy: tip in normal use posture
    s.battery_pct = read_battery_pct();

    return s;
}

StickPacket to_packet(const SensorState &state, uint32_t seq) {
    StickPacket pkt{};
    pkt.protocol_version = PROTOCOL_VERSION;

    pkt.flags = 0;
    if (state.sos_pressed)    pkt.flags |= FLAG_SOS;
    if (state.water_detected) pkt.flags |= FLAG_WATER;
    if (state.fall_detected)  pkt.flags |= FLAG_FALL;
    if (state.calibrated)     pkt.flags |= FLAG_CALIBRATED;

    auto to_mm = [](float m) -> uint16_t {
        if (isnan(m) || m > 9.999f) return PACKET_OUT_OF_RANGE;
        return static_cast<uint16_t>(m * 1000.0f);
    };

    pkt.front_mm   = to_mm(state.front_m);
    pkt.left_mm    = to_mm(state.left_m);
    pkt.right_mm   = to_mm(state.right_m);
    pkt.rear_mm    = to_mm(state.rear_m);
    pkt.down_mm    = to_mm(state.down_m);
    pkt.ir_down_mm = to_mm(state.ir_down_m);
    pkt.battery_pct = state.battery_pct;
    pkt.reserved = 0;
    pkt.seq = seq;
    pkt.uptime_ms = millis();

    return pkt;
}

bool fall_watchdog_tick(bool fall_detected_this_cycle) {
    if (fall_detected_this_cycle && !fall_watchdog_armed) {
        fall_watchdog_armed = true;
        fall_detected_at_ms = millis();
    }

    if (fall_watchdog_armed) {
        bool recovered = read_fsr_ground_contact() && (digitalRead(SOS_BUTTON_PIN) == HIGH);
        if (recovered) {
            fall_watchdog_armed = false;
            return false;
        }
        if (millis() - fall_detected_at_ms > FALL_WATCHDOG_NO_RECOVERY_MS) {
            return true; // force SOS: fall + no recovery
        }
    }
    return false;
}

} // namespace sensors
