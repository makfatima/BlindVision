// BlindVision Smart Stick - BLE server implementation.
// See include/ble_server.h.

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "ble_server.h"

namespace {

BLEServer *g_server = nullptr;
BLECharacteristic *g_packet_char = nullptr;
volatile bool g_connected = false;

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer *server) override {
        g_connected = true;
        Serial.println("[ble] Goggles connected.");
    }
    void onDisconnect(BLEServer *server) override {
        g_connected = false;
        Serial.println("[ble] Goggles disconnected; resuming advertising.");
        server->startAdvertising();
    }
};

} // namespace

namespace ble_server {

void begin() {
    BLEDevice::init(DEVICE_NAME);

    // Bluetooth AES-CCM pairing/bonding encryption (Section III) -
    // relies on the ESP32 BLE stack's standard security manager rather
    // than an application-layer cipher.
    BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT);

    g_server = BLEDevice::createServer();
    g_server->setCallbacks(new ServerCallbacks());

    BLEService *service = g_server->createService(SERVICE_UUID);

    g_packet_char = service->createCharacteristic(
        PACKET_CHAR_UUID,
        BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ
    );
    g_packet_char->addDescriptor(new BLE2902());

    service->start();

    BLEAdvertising *advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(SERVICE_UUID);
    advertising->setScanResponse(true);
    BLEDevice::startAdvertising();

    Serial.println("[ble] Advertising as " + String(DEVICE_NAME));
}

bool is_connected() {
    return g_connected;
}

void notify_packet(const StickPacket &pkt) {
    if (!g_connected || g_packet_char == nullptr) {
        return;
    }
    g_packet_char->setValue(reinterpret_cast<uint8_t *>(const_cast<StickPacket *>(&pkt)), sizeof(StickPacket));
    g_packet_char->notify();
}

} // namespace ble_server
