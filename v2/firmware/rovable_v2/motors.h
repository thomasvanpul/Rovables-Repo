// Two N20 motors through a DRV8833: one PWM pin and one low pin per direction (fast decay).
#pragma once
#include "config.h"

namespace motors {

inline bool active = false;

inline void drive(uint8_t in1, uint8_t in2, uint8_t duty, bool forward) {
  ledcWrite(forward ? in1 : in2, duty);
  ledcWrite(forward ? in2 : in1, 0);
}

inline void set(uint8_t m1_pwm, uint8_t m2_pwm, bool m1_forward, bool m2_forward) {
  drive(PIN_M1_IN1, PIN_M1_IN2, m1_pwm, m1_forward != M1_INVERT);
  drive(PIN_M2_IN1, PIN_M2_IN2, m2_pwm, m2_forward != M2_INVERT);
  active = m1_pwm > 0 || m2_pwm > 0;
}

inline void stop() { set(0, 0, true, true); }

inline bool begin() {
  bool ok = true;
  for (uint8_t pin : {PIN_M1_IN1, PIN_M1_IN2, PIN_M2_IN1, PIN_M2_IN2}) {
    ok = ledcAttach(pin, PWM_HZ, PWM_BITS) && ok;
  }
  stop();
  return ok;
}

}  // namespace motors
