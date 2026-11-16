#!/usr/bin/env python3
"""Drive a Rovable v2 from the Mac over BLE. This replaces the original USB base station and its
Processing sketch.

    pip install bleak
    python v2/host/rovable_ble.py listen                       # print telemetry
    python v2/host/rovable_ble.py drive --left 150 --right 150 --seconds 2
    python v2/host/rovable_ble.py drive --left 120 --right -120 --seconds 1   # turn on the spot

The packet functions are plain Python and are tested without a radio (test_rovable_ble.py). The BLE part
has not been run against a robot yet.
"""
import argparse
import asyncio
import struct
from dataclasses import dataclass

BLE_NAME = "Rovable-v2"
UUID_COMMAND = "116212bf-f13e-4588-a099-80a2e9a3cecc"
UUID_TELEMETRY = "17af610f-9ec2-4a70-a850-e3393a94b8ea"
PACKET_SIZE = 7
OP_MOTOR_CRL = 0x02
OP_ZERO_YAW = 0x10
TELEMETRY_FORMAT = "<I3h3hhBB"            # matches struct Telemetry in rovable_v2.ino
TELEMETRY_SIZE = struct.calcsize(TELEMETRY_FORMAT)
RESEND_S = 0.2                            # under the firmware's 0.5 s command timeout
SCAN_TIMEOUT_S = 10.0
MAX_PWM = 255


@dataclass(frozen=True)
class Telemetry:
    ms: int
    accel: tuple[int, int, int]
    gyro: tuple[int, int, int]
    yaw_deg: float
    imu_ok: bool
    motors_running: bool
    seq: int


def motor_packet(left: int, right: int) -> bytes:
    """Signed speeds, -255 to 255, as the original 7-byte motor packet. Left is motor 1 (front unit)."""
    for name, v in (("left", left), ("right", right)):
        if not -MAX_PWM <= v <= MAX_PWM:
            raise ValueError(f"{name} speed {v} is outside -{MAX_PWM} to {MAX_PWM}")
    return bytes([OP_MOTOR_CRL, abs(left), abs(right), int(left >= 0), int(right >= 0), 0, 0])


def zero_yaw_packet() -> bytes:
    return bytes([OP_ZERO_YAW] + [0] * (PACKET_SIZE - 1))


def parse_telemetry(data: bytes) -> Telemetry:
    if len(data) != TELEMETRY_SIZE:
        raise ValueError(f"telemetry is {len(data)} bytes, expected {TELEMETRY_SIZE}")
    ms, ax, ay, az, gx, gy, gz, yaw, flags, seq = struct.unpack(TELEMETRY_FORMAT, data)
    return Telemetry(ms, (ax, ay, az), (gx, gy, gz), yaw / 100.0, bool(flags & 1), bool(flags & 2), seq)


async def connect():
    from bleak import (  # imported here so the packet code needs no radio
        BleakClient,
        BleakScanner,
    )
    device = await BleakScanner.find_device_by_name(BLE_NAME, timeout=SCAN_TIMEOUT_S)
    if device is None:
        raise SystemExit(f"No device advertising as {BLE_NAME} within {SCAN_TIMEOUT_S:.0f} s")
    return BleakClient(device)


async def listen(seconds: float) -> None:
    async with await connect() as client:
        await client.start_notify(UUID_TELEMETRY, lambda _, data: print(parse_telemetry(bytes(data))))
        await asyncio.sleep(seconds)


async def drive(left: int, right: int, seconds: float) -> None:
    packet = motor_packet(left, right)
    async with await connect() as client:
        loop = asyncio.get_running_loop()
        end = loop.time() + seconds
        try:
            while loop.time() < end:
                await client.write_gatt_char(UUID_COMMAND, packet, response=False)
                await asyncio.sleep(RESEND_S)
        finally:
            await client.write_gatt_char(UUID_COMMAND, motor_packet(0, 0), response=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Drive a Rovable v2 over BLE")
    sub = ap.add_subparsers(dest="cmd", required=True)
    li = sub.add_parser("listen", help="print telemetry")
    li.add_argument("--seconds", type=float, default=10.0)
    dr = sub.add_parser("drive", help="run both motors for a time, then stop")
    dr.add_argument("--left", type=int, required=True)
    dr.add_argument("--right", type=int, required=True)
    dr.add_argument("--seconds", type=float, default=1.0)
    args = ap.parse_args()
    if args.cmd == "listen":
        asyncio.run(listen(args.seconds))
    else:
        asyncio.run(drive(args.left, args.right, args.seconds))


if __name__ == "__main__":
    main()
