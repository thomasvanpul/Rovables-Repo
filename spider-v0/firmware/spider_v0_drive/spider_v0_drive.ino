// Spider v0 drive test: ESP32-S3 makes its own WiFi, your phone is the joystick.
// 19 Nov 2026. Board: ESP32-S3-DevKitC-1 (Arduino core 2.x or 3.x, uses analogWrite).
//
// 1. Flash this. 2. On the phone join WiFi "spider-v0", password "spiderbot".
// 3. Open http://192.168.4.1  -> hold the arrows; the slider sets speed.
//
// Driver: TB6612 (preferred: VM up to 13.5 V, ~0.5 V drop) or L298N (drops ~2 V, needs
// 7-9 V on its 12V pin for the motors to see ~5 V). The pin roles are the same:
//   motor A: A_IN1, A_IN2, A_PWM   (TB6612 AIN1/AIN2/PWMA, L298N IN1/IN2/ENA, take the ENA jumper off)
//   motor B: B_IN1, B_IN2, B_PWM   (TB6612 BIN1/BIN2/PWMB, L298N IN3/IN4/ENB, take the ENB jumper off)
//   TB6612 STBY -> 3V3.  Grounds of ESP, driver and motor supply all tied together.
// If the bot spins when you press forward, one motor is wired backwards: set A_REVERSED or B_REVERSED.
// Motor A = the roller at +X (see spider-v0/README.md), motor B = the roller at -X.

#include <WiFi.h>
#include <WebServer.h>

const int A_IN1 = 4, A_IN2 = 5, A_PWM = 6;
const int B_IN1 = 7, B_IN2 = 15, B_PWM = 16;
const bool A_REVERSED = false;
const bool B_REVERSED = true;   // the two units face opposite ways, so one is mirrored by default

WebServer server(80);
int speedPct = 70;
unsigned long holdUntil = 0;     // motors stop after this (deadman)
const unsigned long DEADMAN_MS = 400;   // stop if the phone stops sending (finger lifted, WiFi drop)

void motor(int in1, int in2, int pwm, int v, bool rev) {   // v in -255..255
  if (rev) v = -v;
  if (v > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW); }
  else if (v < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else            { digitalWrite(in1, LOW);  digitalWrite(in2, LOW); }
  analogWrite(pwm, abs(v));
}

void drive(int left, int right) {   // -100..100 each
  int s = map(speedPct, 0, 100, 0, 255);
  motor(A_IN1, A_IN2, A_PWM, left * s / 100, A_REVERSED);
  motor(B_IN1, B_IN2, B_PWM, right * s / 100, B_REVERSED);
}

const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1,user-scalable=no">
<style>body{font-family:system-ui;background:#111;color:#eee;text-align:center;margin:0;padding:16px;touch-action:none}
.g{display:grid;grid-template-columns:repeat(3,96px);gap:10px;justify-content:center;margin:24px 0}
button{height:96px;font-size:34px;border:0;border-radius:18px;background:#2a2a2e;color:#eee}
button:active{background:#c49a4a;color:#111}input{width:80%}</style></head><body>
<h2>spider v0</h2><div class=g>
<span></span><button data-l=100 data-r=100>&#9650;</button><span></span>
<button data-l=-100 data-r=100>&#10226;</button><button data-l=0 data-r=0>&#9632;</button><button data-l=100 data-r=-100>&#10227;</button>
<span></span><button data-l=-100 data-r=-100>&#9660;</button><span></span></div>
speed <span id=v>70</span>%<br><input id=s type=range min=20 max=100 value=70>
<p style="opacity:.6">hold a button; release stops it</p>
<script>let cur=null;function send(l,r){fetch('/d?l='+l+'&r='+r+'&s='+s.value).catch(()=>{})}
setInterval(()=>{if(cur)send(cur[0],cur[1])},150);
document.querySelectorAll('button').forEach(b=>{const go=e=>{e.preventDefault();cur=[b.dataset.l,b.dataset.r];send(cur[0],cur[1])};
const stop=e=>{e.preventDefault();cur=null;send(0,0)};b.addEventListener('pointerdown',go);b.addEventListener('pointerup',stop);b.addEventListener('pointerleave',stop)});
s.oninput=()=>v.textContent=s.value;</script></body></html>)HTML";

void setup() {
  Serial.begin(115200);
  int pins[] = {A_IN1, A_IN2, A_PWM, B_IN1, B_IN2, B_PWM};
  for (int p : pins) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
  WiFi.softAP("spider-v0", "spiderbot");
  server.on("/", [] { server.send_P(200, "text/html", PAGE); });
  server.on("/d", [] {
    int l = constrain(server.arg("l").toInt(), -100, 100);
    int r = constrain(server.arg("r").toInt(), -100, 100);
    if (server.hasArg("s")) speedPct = constrain(server.arg("s").toInt(), 0, 100);
    drive(l, r);
    holdUntil = millis() + DEADMAN_MS;
    server.send(200, "text/plain", "ok");
  });
  server.begin();
  Serial.println("spider-v0 up: join WiFi spider-v0 / spiderbot, open http://192.168.4.1");
}

void loop() {
  server.handleClient();
  if ((long)(millis() - holdUntil) > 0) drive(0, 0);
  // serial fallback: type w a s d x (+ Enter) in the Serial Monitor
  if (Serial.available()) {
    char c = Serial.read();
    holdUntil = millis() + 2000;   // serial commands run for 2 s
    if (c == 'w') drive(100, 100); else if (c == 's') drive(-100, -100);
    else if (c == 'a') drive(-100, 100); else if (c == 'd') drive(100, -100); else if (c == 'x') drive(0, 0);
  }
}
