// BlindVision Smart Stick - sensor sampling
//
// Runs on Core 0: polls all sensors at ~10-20 Hz and applies local
// safety logic (Section III). Produces a fully populated StickPacket
// each cycle for Core 1 to broadcast over BLE.

#pragma once
#include "packet.h"

struct SensorState {
    float front_m, left_m, right_m, rear_m, down_m;
    float ir_down_m;
    bool water_detected;
    bool fall_detected;
    bool sos_pressed;
    bool calibrated;
    uint8_t battery_pct;
};

namespace sensors {

// Call once from setup() on Core 0.
void begin();

// Call every cycle (~10-20 Hz) from the Core 0 task loop.
// Reads all ultrasonic/IR/water/IMU/FSR/SOS inputs and applies the
// local drop-off / fall watchdog logic described in Section III-IV.
SensorState sample();

// Builds the wire packet from a SensorState + running sequence counter.
StickPacket to_packet(const SensorState &state, uint32_t seq);

// Fall watchdog: forces an SOS signal if a fall is detected followed by
// no recovery within fall_watchdog_no_recovery_s (config/fusion_config.yaml).
// Call once per cycle; internally tracks time since last fall event.
bool fall_watchdog_tick(bool fall_detected_this_cycle);

} // namespace sensors
