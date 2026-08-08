// BlindVision Smart Stick <-> Smart Goggles wire packet.
//
// Mirrors goggles/ble/packet.py exactly. 24 bytes, little-endian
// (native ESP32/ARM byte order, no swap needed). Keep both files in
// sync if this layout ever changes.

#pragma once
#include <cstdint>

#pragma pack(push, 1)
struct StickPacket {
    uint8_t  protocol_version;   // = 1
    uint8_t  flags;              // bit0 SOS, bit1 water, bit2 fall, bit3 calibrated
    uint16_t front_mm;           // 0-9999, 0xFFFF = out of range
    uint16_t left_mm;
    uint16_t right_mm;
    uint16_t rear_mm;
    uint16_t down_mm;            // downward ultrasonic (near-field ground sensing)
    uint16_t ir_down_mm;         // downward IR (drop-off sensing)
    uint8_t  battery_pct;        // 0-100
    uint8_t  reserved;
    uint32_t seq;                // monotonic packet sequence number
    uint32_t uptime_ms;
};
#pragma pack(pop)

static_assert(sizeof(StickPacket) == 24, "StickPacket must stay 24 bytes");

#define FLAG_SOS         0x01
#define FLAG_WATER       0x02
#define FLAG_FALL        0x04
#define FLAG_CALIBRATED  0x08

#define PACKET_OUT_OF_RANGE 0xFFFF
#define PROTOCOL_VERSION    1
