// BlindVision Smart Stick - pin assignments (ESP32 DevKit V1)
//
// Sensor inventory per Section III:
//   5x ultrasonic (front, left, right, rear @ ~90deg intervals, +1 angled
//      downward for near-field ground sensing)
//   2x IR proximity (aimed downward: edges/stairs)
//   1x resistive water-level sensor (tip)
//   1x IMU (MPU9250) for falls/knocks
//   1x FSR (force-sensitive resistor) at the tip, ground-contact confirm
//   1x large SOS pushbutton on the handle
// Outputs: vibration motor, piezo buzzer, LED safety light.
//
// NOTE: pin numbers below are a reference assignment consistent with
// common ESP32 DevKit V1 wiring practice; adjust to match your build's
// physical wiring before flashing.

#pragma once

// --- Ultrasonic sensors (HC-SR04 style: trig/echo pairs) -----------------
#define US_FRONT_TRIG   5
#define US_FRONT_ECHO   18
#define US_LEFT_TRIG    19
#define US_LEFT_ECHO    21
#define US_RIGHT_TRIG   22
#define US_RIGHT_ECHO   23
#define US_REAR_TRIG    13
#define US_REAR_ECHO    12
#define US_DOWN_TRIG    14
#define US_DOWN_ECHO    27

// --- IR proximity sensors (downward, drop-off / stair detection) ---------
#define IR_DOWN_1_PIN   34   // ADC1_CH6, input-only
#define IR_DOWN_2_PIN   35   // ADC1_CH7, input-only

// --- Water sensor (resistive, tip) ----------------------------------------
#define WATER_SENSOR_PIN 32  // ADC1_CH4

// --- IMU (MPU9250, I2C) ----------------------------------------------------
#define IMU_SDA_PIN     25
#define IMU_SCL_PIN     26
#define IMU_I2C_ADDR    0x68

// --- Force-sensitive resistor (tip, ground-contact confirmation) ---------
#define FSR_PIN         33   // ADC1_CH5

// --- SOS pushbutton (handle) -----------------------------------------------
#define SOS_BUTTON_PIN  4    // active-low, internal pull-up

// --- Outputs -----------------------------------------------------------------
#define VIBRATION_MOTOR_PIN 15
#define BUZZER_PIN          2
#define LED_SAFETY_PIN      16

// --- Power -----------------------------------------------------------------
// 3.7V 18650 Li-ion, 5000 mAh, TP4056 charge IC.
#define BATTERY_ADC_PIN 36   // ADC1_CH0, resistor-divider battery sense
