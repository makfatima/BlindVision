/*
 * BLE peripheral (GATT server) exposing the Smart Stick's sensor packet to
 * the Smart Goggles' BLE central (Bluetooth 4.2, per the ESP32-WROOM-32
 * module -- Section III). Core 1 manages the BLE stack and state machine.
 */

#ifndef BLINDVISION_STICK_BLE_PERIPHERAL_H
#define BLINDVISION_STICK_BLE_PERIPHERAL_H

#include "sensors.h"

void ble_peripheral_init();
bool ble_peripheral_is_connected();

// Serializes a SensorSnapshot into the 24-byte packet format documented in
// smart_goggles/ble/stick_link.py and sends it as a BLE notification.
void ble_peripheral_send_snapshot(const SensorSnapshot& snapshot, uint32_t seq);

// Registers a callback invoked when the goggles write a haptic-pattern
// command to the RX characteristic.
typedef void (*HapticCommandCallback)(const char* patternName);
void ble_peripheral_on_haptic_command(HapticCommandCallback cb);

#endif  // BLINDVISION_STICK_BLE_PERIPHERAL_H
