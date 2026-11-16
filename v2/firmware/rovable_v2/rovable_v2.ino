// Rovable v2 firmware skeleton: motor drive, IMU and BLE on an ESP32-C3 or ESP32-S3.
//
// Replaces the original robot's SAMD21 + nRF24L01+ and its USB base station: the Mac or a phone connects
// to the robot directly over BLE. The command packet keeps the original 7-byte layout and op codes.
//
// Compiles with arduino-cli (esp32 core 3.x). Not yet run on hardware.
//   arduino-cli compile --fqbn esp32:esp32:esp32c3 v2/firmware/rovable_v2
//   arduino-cli compile --fqbn esp32:esp32:esp32s3 v2/firmware/rovable_v2

#include <BLEDevice.h>
#include <BLEServer.h>

#include "config.h"
#include "imu.h"
#include "motors.h"

namespace {

// Telemetry notification, 20 bytes so it fits the default BLE packet. Little-endian.
struct __attribute__((packed)) Telemetry {
  uint32_t ms;
  int16_t accel[3];
  int16_t gyro[3];
  int16_t yaw_cdeg;  // hundredths of a degree, -18000 to 18000
  uint8_t flags;     // bit 0 IMU answering, bit 1 motors running
  uint8_t seq;
};
static_assert(sizeof(Telemetry) == 20, "telemetry must fit one default BLE notification");

BLECharacteristic *telemetry_char = nullptr;
volatile bool connected = false;
volatile uint32_t last_command_ms = 0;
volatile bool zero_yaw_requested = false;
uint32_t last_telemetry_ms = 0;
uint8_t seq = 0;

void handle_packet(const uint8_t *p, size_t n) {
  if (n != PACKET_SIZE) return;
  switch (p[0]) {
    case OP_MOTOR_CRL:
      motors::set(p[1], p[2], p[3] != 0, p[4] != 0);
      last_command_ms = millis();
      break;
    case OP_ZERO_YAW:
      zero_yaw_requested = true;  // done in loop(), which owns the IMU state
      break;
    case OP_IGNORE:
    default:
      break;
  }
}

class CommandCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    handle_packet(c->getData(), c->getLength());
  }
};

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { connected = true; }
  void onDisconnect(BLEServer *server) override {
    connected = false;
    motors::stop();
    server->startAdvertising();
  }
};

void start_ble() {
  BLEDevice::init(BLE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *service = server->createService(UUID_SERVICE);
  BLECharacteristic *command = service->createCharacteristic(
      UUID_COMMAND, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  command->setCallbacks(new CommandCallbacks());
  // The core adds the notification descriptor (0x2902) itself for a notify characteristic.
  telemetry_char = service->createCharacteristic(UUID_TELEMETRY, BLECharacteristic::PROPERTY_NOTIFY);
  service->start();
  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(UUID_SERVICE);
  advertising->setScanResponse(true);
  BLEDevice::startAdvertising();
}

void send_telemetry(uint32_t now) {
  Telemetry t = {};
  t.ms = now;
  memcpy(t.accel, imu::last.accel, sizeof(t.accel));
  memcpy(t.gyro, imu::last.gyro, sizeof(t.gyro));
  t.yaw_cdeg = (int16_t)(imu::yaw_deg * 100.0f);
  t.flags = (imu::ok ? 0x01 : 0x00) | (motors::active ? 0x02 : 0x00);
  t.seq = seq++;
  telemetry_char->setValue((uint8_t *)&t, sizeof(t));
  telemetry_char->notify();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  const bool motors_ok = motors::begin();
  const bool imu_ok = imu::begin();
  start_ble();
  Serial.printf("Rovable v2: motors %s, IMU %s, advertising as %s\n", motors_ok ? "ok" : "PWM attach failed",
                imu_ok ? "ok" : "not answering", BLE_NAME);
}

void loop() {
  const uint32_t now = millis();
  if (zero_yaw_requested) {
    zero_yaw_requested = false;
    imu::zero_yaw();
  }
  imu::update();
  if (motors::active && now - last_command_ms > COMMAND_TIMEOUT_MS) {
    motors::stop();  // link lost or the host stopped sending
  }
  if (connected && now - last_telemetry_ms >= TELEMETRY_PERIOD_MS) {
    last_telemetry_ms = now;
    send_telemetry(now);
  }
  delay(2);
}
