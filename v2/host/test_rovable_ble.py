"""Packet tests for the host script. No radio needed: python -m pytest v2/host"""
import pathlib
import re
import struct

import pytest
import rovable_ble as rb

CONFIG = (pathlib.Path(__file__).resolve().parents[1] / "firmware" / "rovable_v2" / "config.h").read_text()


def firmware_value(name: str) -> str:
    return re.search(rf"{name}(?:\[\])? = \"?([^\";]+)\"?;", CONFIG).group(1)


def test_motor_packet_keeps_the_original_seven_byte_layout():
    assert rb.motor_packet(150, -90) == bytes([0x02, 150, 90, 1, 0, 0, 0])


def test_motor_packet_stop_is_all_zero_speed():
    assert rb.motor_packet(0, 0)[1:3] == b"\x00\x00"


def test_motor_packet_rejects_speed_out_of_range():
    with pytest.raises(ValueError):
        rb.motor_packet(256, 0)


def test_zero_yaw_packet_is_packet_sized():
    assert len(rb.zero_yaw_packet()) == rb.PACKET_SIZE


def test_telemetry_round_trip():
    raw = struct.pack(rb.TELEMETRY_FORMAT, 1234, 1, -2, 16384, 10, -20, 30, -4550, 0b11, 7)
    t = rb.parse_telemetry(raw)
    assert (t.ms, t.accel, t.gyro, t.yaw_deg, t.imu_ok, t.motors_running, t.seq) == (
        1234, (1, -2, 16384), (10, -20, 30), -45.5, True, True, 7)


def test_telemetry_is_twenty_bytes_like_the_firmware_struct():
    assert rb.TELEMETRY_SIZE == 20


def test_telemetry_rejects_wrong_length():
    with pytest.raises(ValueError):
        rb.parse_telemetry(b"\x00" * 19)


@pytest.mark.parametrize("host, firmware", [
    (rb.BLE_NAME, "BLE_NAME"), (rb.UUID_COMMAND, "UUID_COMMAND"), (rb.UUID_TELEMETRY, "UUID_TELEMETRY")])
def test_host_names_match_the_firmware_config(host, firmware):
    assert host == firmware_value(firmware)


@pytest.mark.parametrize("host, firmware", [
    (rb.PACKET_SIZE, "PACKET_SIZE"), (rb.OP_MOTOR_CRL, "OP_MOTOR_CRL"), (rb.OP_ZERO_YAW, "OP_ZERO_YAW")])
def test_host_numbers_match_the_firmware_config(host, firmware):
    assert host == int(firmware_value(firmware), 0)


def test_resend_is_inside_the_firmware_command_timeout():
    assert rb.RESEND_S * 1000 < int(firmware_value("COMMAND_TIMEOUT_MS"))
