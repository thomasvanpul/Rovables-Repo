// Rovable v2 firmware configuration: pins, radio names and timing. Everything tunable is here.
#pragma once
#include <Arduino.h>

// ---- Pins. ASSUMED wiring, not yet built: change to match the board on the bench. ----
#if CONFIG_IDF_TARGET_ESP32C3
// ESP32-C3 SuperMini. Avoids the strapping pins 2, 8 and 9.
constexpr uint8_t PIN_M1_IN1 = 0;   // DRV8833 AIN1, front unit (roller on the left)
constexpr uint8_t PIN_M1_IN2 = 1;   // DRV8833 AIN2
constexpr uint8_t PIN_M2_IN1 = 3;   // DRV8833 BIN1, back unit (roller on the right)
constexpr uint8_t PIN_M2_IN2 = 4;   // DRV8833 BIN2
constexpr uint8_t PIN_SDA = 6;      // MPU6050
constexpr uint8_t PIN_SCL = 7;
#elif CONFIG_IDF_TARGET_ESP32S3
// ESP32-S3 dev board. Avoids the strapping pins 0, 3, 45, 46 and the USB pins 19, 20.
constexpr uint8_t PIN_M1_IN1 = 4;
constexpr uint8_t PIN_M1_IN2 = 5;
constexpr uint8_t PIN_M2_IN1 = 6;
constexpr uint8_t PIN_M2_IN2 = 7;
constexpr uint8_t PIN_SDA = 8;
constexpr uint8_t PIN_SCL = 9;
#else
#error "Rovable v2 firmware targets ESP32-C3 and ESP32-S3"
#endif

// The two units sit rotated 180 degrees from each other, so one motor turns the other way to go forward.
constexpr bool M1_INVERT = false;
constexpr bool M2_INVERT = true;

// ---- Motor drive ----
constexpr uint32_t PWM_HZ = 20000;          // above hearing
constexpr uint8_t PWM_BITS = 8;             // duty 0 to 255, the same range as the original packet
constexpr uint32_t COMMAND_TIMEOUT_MS = 500;  // motors stop if no command arrives for this long

// ---- IMU (MPU6050 over I2C, raw registers, no library) ----
constexpr uint8_t MPU_ADDRESS = 0x68;       // same address as the original firmware
constexpr uint32_t I2C_HZ = 400000;
constexpr uint16_t GYRO_BIAS_SAMPLES = 200;  // taken at boot with the robot still
constexpr float GYRO_LSB_PER_DPS = 131.0f;  // MPU6050 at its default +-250 deg/s range

// ---- BLE ----
constexpr char BLE_NAME[] = "Rovable-v2";
constexpr char UUID_SERVICE[] = "c2e4bc54-9aad-4f3a-8c65-240860d0d44f";
constexpr char UUID_COMMAND[] = "116212bf-f13e-4588-a099-80a2e9a3cecc";    // write, 7 bytes
constexpr char UUID_TELEMETRY[] = "17af610f-9ec2-4a70-a850-e3393a94b8ea";  // notify, 20 bytes
constexpr uint32_t TELEMETRY_PERIOD_MS = 50;  // 20 Hz; the original radio link ran at 10 Hz

// ---- Command packet: the original 7-byte layout, so the op codes keep their meaning ----
constexpr size_t PACKET_SIZE = 7;
constexpr uint8_t OP_IGNORE = 0x01;      // original
constexpr uint8_t OP_MOTOR_CRL = 0x02;   // original: [op, m1_pwm, m2_pwm, m1_dir, m2_dir, 0, 0]
constexpr uint8_t OP_ZERO_YAW = 0x10;    // v2: reset the integrated heading
