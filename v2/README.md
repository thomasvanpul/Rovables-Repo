# Rovable v2 (Imperial, 2026)

A larger Rovable built from parts that are easy to get: two N20 gear motors, two 8.92 x 25 mm N42 rod magnets
used as the wheels, an ESP32-C3 or ESP32-S3 talking to a Mac over Bluetooth Low Energy, and a body that prints
on an ordinary FDM printer. Nothing here is the original authors' work; their design is in the folders above
this one, unchanged.

![Rovable v2 in Fusion](cad/out/fusion_iso.png)
![Underside: the two rollers, and the two loose magnets that sit inside the shirt](cad/out/fusion_under.png)

State on 16 Nov 2026: modelled, sliced, firmware compiles. **Not printed, not wired, not driven.**

## What changes from the original

| | Original (2016) | v2 |
|---|---|---|
| Size | 40 x 26 x 26 mm | 80 x 40 x 22 mm |
| Motors | 6 mm planetary gear motors, 136:1 | N20 gear motors |
| Wheels | 9 mm magnet wheels with neoprene tyres | Printed 12 mm rollers, each holding one rod magnet |
| Behind the fabric | One magnetic rod | Two loose rod magnets, one under each roller, nothing else |
| Processor and radio | SAMD21 with an nRF24L01+, and a base station on USB | One ESP32 with BLE built in; the Mac is the base station |
| Boards | Custom four-layer board, 0.57 mm thick | Three bought modules on a printed tray |
| Printing | 25 micron resin | PLA on a Bambu P1S, 0.4 mm nozzle, no supports |
| Wheel encoders | Infrared, on a flex cable | None yet |

The reason for the change of radio is in the paper's own limits section: a base station that manages about
three robots before packets collide, and a call for a faster processor to run a proper filter. The reason for
the change of board is in `/electronics/bom`: JLCPCB will not make the original board as drawn (four layers at
0.57 mm), and its radio and motor driver chips were out of stock there on 16 Nov 2026.

## How it is laid out

Two identical units, each one N20 motor driving one magnet roller, sit side by side and rotated 180 degrees from
each other. The front roller is on the left and the back roller is on the right, so the two rollers steer the
robot like two wheels while the motors lie alongside each other and keep it short. Each roller hangs on the
motor's D shaft at one end and on an M3 screw through the chassis wall at the other.

The idea that the magnet should be the driven roller, and the fits for the motor and the magnet, come from a
one-roller test rig built the same day. `evidence/README.md` says what that test showed and what it did not.

## Files

| Path | What |
|---|---|
| `cad/rovable_v2_geom.py` | Every dimension, as named parameters at the top, and the shape of each part |
| `cad/build.py` | Makes the STLs in print orientation, checks them, and slices the plate |
| `cad/fusion_view.py` | Opens the same geometry in Autodesk Fusion and saves the two views above |
| `cad/out/stl/` | The five printed parts |
| `cad/out/plates/rovable_v2_P1S_0.4mm.3mf` | One plate: a full robot plus a spare pair of rollers and caps |
| `cad/out/rovable_v2.f3d` | The Fusion model |
| `firmware/rovable_v2/` | Arduino sketch: motor drive, IMU, BLE |
| `host/rovable_ble.py` | Drives the robot from the Mac |
| `evidence/` | The test rig this design starts from |

## Print

```
python v2/cad/build.py --slice
```

needs `manifold3d`, `trimesh`, `numpy`, and Bambu Studio for the slice. Measured on 16 Nov 2026: all five parts
watertight and one solid each; no two parts of the assembly overlap, bought parts included; the plate slices
with return code 0 as 12 objects, 1 h 14 min and 39.3 g of PLA at 0.2 mm layers, three walls, 20% infill, no
supports. A robot's printed parts weigh at most 42.8 g (if printed solid).

| Part | Copies per robot | On the plate | Printed |
|---|---|---|---|
| `chassis` | 1 | 1 | deck on the bed |
| `tray` | 1 | 1 | floor on the bed |
| `roller_body` | 2 | 4 | hub end down, bore up |
| `roller_cap` | 2 | 4 | flange down |
| `motor_cap` | 2 | 2 | flange down |

## Parts to gather

- 2 N20 gear motors with a 3 mm D shaft. Pick a slow ratio; the original used 136:1.
- 4 N42 rod magnets, 8.92 x 25 mm: two in the rollers, two loose inside the shirt. With only two magnets, an
  8 mm steel rod can stand in behind the fabric, which holds less.
- ESP32-C3 SuperMini (or an ESP32-S3 board, which needs a different tray pocket).
- DRV8833 dual motor driver module.
- GY-521 (MPU6050) module. A magnetometer is no use next to the wheel magnets, as the original authors found.
- One-cell LiPo that fits 30 x 12 x 4 mm (size 401230), and a way to charge it.
- 4 M3 x 10 screws: two axles, two for the tray.

## Assemble

1. Push a magnet into each roller body and press the cap in.
2. Drop each roller into its well from below. Push the motor into its tunnel from the end of the chassis so the
   D shaft enters the roller. Fit the motor cap, wires through its slot.
3. Run an M3 screw through the end wall into the roller cap. It cuts its own thread and turns with the roller.
4. Screw the tray down, seat the three boards and the battery, and wire to the pins in `firmware/rovable_v2/config.h`.

## Firmware

```
arduino-cli compile --fqbn esp32:esp32:esp32c3 v2/firmware/rovable_v2
arduino-cli compile --fqbn esp32:esp32:esp32s3 v2/firmware/rovable_v2
```

Both compile with no warnings on arduino-cli 1.6.0 with the esp32 core 3.3.12 (645,789 and 598,055 bytes).
It has not been flashed to a board.

It is a skeleton. The robot advertises as `Rovable-v2`. One characteristic takes the original 7-byte motor
packet, with the same op codes, so the original control software's packets still mean the same thing. A second
sends 20 bytes of telemetry 20 times a second: raw accelerometer and gyro, and a heading integrated from the
gyro. The motors stop if no command arrives for half a second or the link drops.

`host/rovable_ble.py` drives it from a Mac (`pip install bleak`). Its packet code is tested against the
firmware's own constants (`python -m pytest v2/host`, 14 tests); the radio part has not met a robot.

## Not done, and not known

Every number that was not measured or printed is a named parameter marked ASSUMED or V4 in
`cad/rovable_v2_geom.py` and `firmware/rovable_v2/config.h`. The ones that matter most:

- **The module sizes.** The tray pockets are drawn from typical outlines for the ESP32-C3 SuperMini, the
  DRV8833 module, the GY-521 and a 401230 cell. Measure the boards before printing the tray.
- **The N20 body length (24 mm) and shaft length (10 mm).** These vary between sellers.
- **Each magnet next to the other unit's motor.** A roller magnet runs 13.5 mm from the steel can of the
  neighbouring motor. If that pull drags on the roller, raise `AXIS_PITCH`.
- **Turning.** The rollers are 25 mm wide and 33 mm apart centre to centre, and one sits ahead of the other, so
  a turn has to scrub them sideways across the fabric. Whether the motors can do that against the clamp is
  the first thing to find out.
- **Whether a 3.7 V cell turns the N20s hard enough.** If not, the fix is a boost converter or a two-cell pack.
- **The pin assignment.** Chosen to avoid the boot strapping pins; no board has been wired to it.

Not started: wheel encoders and so any dead reckoning, the Kalman filter and 3D localisation the paper asks for,
charging, and anything that gets the robot over a seam or onto an arm.
