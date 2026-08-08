/*
 * BlindVision proof-of-concept firmware (ESP32-CAM, AI-Thinker, OV2640)
 *
 * Section V.A: "On the firmware side, the ESP32 triggers a buzzer
 * pattern (pulse count scaled to priority: 3 = high, 2 = medium, 1 =
 * low) and relays the spoken-guidance string to a paired phone over
 * Bluetooth (HC-05) for TTS output; a 3-second cooldown per object
 * class prevents repeated alerts for a stationary obstacle."
 *
 * Flow: capture JPEG -> POST to FastAPI /detect endpoint over Wi-Fi ->
 * parse JSON -> buzzer pattern + HC-05 relay of top_message.
 *
 * Board: AI-Thinker ESP32-CAM. Requires the `esp32` board package and
 * `ArduinoJson` library.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "camera_pins.h"   // AI-Thinker pin map (board package standard header)

// ---- Configuration ---------------------------------------------------------
const char *WIFI_SSID = "YOUR_WIFI_SSID";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char *DETECT_ENDPOINT = "http://YOUR_SERVER_HOST:8000/detect";

#define BUZZER_PIN 12
#define HC05_RX 3   // ESP32-CAM UART0 RX (shared with USB during flashing)
#define HC05_TX 1   // ESP32-CAM UART0 TX

constexpr uint32_t CAPTURE_INTERVAL_MS = 800;   // ~0.7-0.9s capture-to-alert budget (Table III)
constexpr uint32_t CLASS_COOLDOWN_MS = 3000;    // 3s per-class cooldown (Section V.A)

String last_alerted_class = "";
uint32_t last_alerted_at_ms = 0;

// ---- Setup ------------------------------------------------------------------

void init_camera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA;   // 640x480, matches image-thirds/height-ratio logic server-side
    config.jpeg_quality = 12;
    config.fb_count = 1;

    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("[cam] Camera init failed.");
    }
}

void setup() {
    Serial.begin(115200);
    Serial1.begin(38400, SERIAL_8N1, HC05_RX, HC05_TX); // HC-05 default AT baud varies; adjust to your module

    pinMode(BUZZER_PIN, OUTPUT);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("[wifi] Connecting");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" connected.");

    init_camera();
}

// ---- Buzzer pattern: pulse count scaled to priority (Section V.A) -------

void buzz_priority(const String &priority) {
    int pulses = 1;
    if (priority == "high") pulses = 3;
    else if (priority == "medium") pulses = 2;
    else if (priority == "low") pulses = 1;

    for (int i = 0; i < pulses; ++i) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(120);
        digitalWrite(BUZZER_PIN, LOW);
        delay(120);
    }
}

// ---- Capture + POST + parse -------------------------------------------------

void capture_and_detect() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[cam] Frame capture failed.");
        return;
    }

    HTTPClient http;
    http.begin(DETECT_ENDPOINT);
    http.addHeader("Content-Type", "image/jpeg");

    int status = http.POST(fb->buf, fb->len);
    esp_camera_fb_return(fb);

    if (status != 200) {
        Serial.printf("[http] POST failed, status=%d\n", status);
        http.end();
        return;
    }

    String payload = http.getString();
    http.end();

    StaticJsonDocument<2048> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (err) {
        Serial.println("[json] Parse error.");
        return;
    }

    JsonArray detections = doc["detections"].as<JsonArray>();
    if (detections.size() == 0) {
        return; // nothing detected this frame
    }

    JsonObject top = detections[0];
    String object_class = top["object_class"].as<String>();
    String priority = top["priority"].as<String>();
    String message = doc["top_message"].as<String>();

    uint32_t now = millis();
    bool same_class_in_cooldown =
        (object_class == last_alerted_class) && (now - last_alerted_at_ms < CLASS_COOLDOWN_MS);

    if (!same_class_in_cooldown) {
        buzz_priority(priority);
        Serial1.println(message); // relay spoken-guidance string to phone (HC-05 -> TTS app)
        last_alerted_class = object_class;
        last_alerted_at_ms = now;
    }
}

void loop() {
    capture_and_detect();
    delay(CAPTURE_INTERVAL_MS);
}
