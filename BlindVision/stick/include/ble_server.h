// BlindVision Smart Stick - BLE 5.0 GATT server (runs on Core 1)
//
// Advertises as "BlindVision-Stick" and continuously notifies the
// packet characteristic with the latest StickPacket. Bonding/pairing
// uses standard Bluetooth AES-CCM encryption (Section III) - no
// separate application-layer cipher is implemented in this prototype.

#pragma once
#include "packet.h"

namespace ble_server {

// UUIDs must match config/fusion_config.yaml [ble] and
// goggles/ble/stick_link.py.
constexpr char SERVICE_UUID[]     = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
constexpr char PACKET_CHAR_UUID[] = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";
constexpr char DEVICE_NAME[]      = "BlindVision-Stick";

void begin();
bool is_connected();
void notify_packet(const StickPacket &pkt);

} // namespace ble_server
