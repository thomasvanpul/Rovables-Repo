// MPU6050 read over I2C and a heading from the gyro alone.
// This is the place the Kalman filter and wheel odometry go; neither is written yet.
#pragma once
#include <Wire.h>
#include "config.h"

namespace imu {

struct Sample {
  int16_t accel[3];
  int16_t gyro[3];
};

inline bool ok = false;
inline Sample last = {};
inline float gyro_z_bias = 0.0f;
inline float yaw_deg = 0.0f;
inline uint32_t last_us = 0;

inline bool write_register(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

inline bool read(Sample &s) {
  Wire.beginTransmission(MPU_ADDRESS);
  Wire.write(0x3B);  // ACCEL_XOUT_H; 14 bytes follow: accel, temperature, gyro
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDRESS, (uint8_t)14) != 14) return false;
  int16_t raw[7];
  for (int16_t &v : raw) {
    const uint8_t hi = Wire.read();
    v = (int16_t)((hi << 8) | Wire.read());
  }
  for (int i = 0; i < 3; i++) {
    s.accel[i] = raw[i];
    s.gyro[i] = raw[4 + i];
  }
  return true;
}

inline bool begin() {
  Wire.begin(PIN_SDA, PIN_SCL, I2C_HZ);
  ok = write_register(0x6B, 0x00);  // PWR_MGMT_1: wake
  if (!ok) return false;
  long sum = 0;
  uint16_t got = 0;
  for (uint16_t i = 0; i < GYRO_BIAS_SAMPLES; i++) {
    Sample s;
    if (read(s)) {
      sum += s.gyro[2];
      got++;
    }
    delay(2);
  }
  ok = got > 0;
  if (ok) gyro_z_bias = (float)sum / got;
  last_us = micros();
  return ok;
}

// Read one sample and integrate the gyro's Z axis (normal to the fabric when the board lies flat on the tray).
inline void update() {
  if (!ok) return;
  Sample s;
  if (!read(s)) return;
  const uint32_t now = micros();
  const float dt = (now - last_us) * 1e-6f;
  last_us = now;
  last = s;
  yaw_deg += (s.gyro[2] - gyro_z_bias) / GYRO_LSB_PER_DPS * dt;
  if (yaw_deg > 180.0f) yaw_deg -= 360.0f;
  if (yaw_deg < -180.0f) yaw_deg += 360.0f;
}

inline void zero_yaw() { yaw_deg = 0.0f; }

}  // namespace imu
