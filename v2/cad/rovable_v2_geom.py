"""Rovable v2 geometry: one source for the STLs, the Fusion model and the checks.

Two magnet rollers, each driven by one N20 gear motor, so the robot can steer (the v4 crawler it grows
from had one roller and went straight only). The two motor-and-roller units are identical and sit
rotated 180 degrees about Z from each other: the front roller is on the left, the back roller on the right.

Every function takes a kernel `k` with box, cylx, cylz, U (union) and D (difference). build.py passes a
manifold3d kernel, fusion_view.py passes a Fusion one, so both draw from the same numbers.

Frame (mm): X = roller axes, Y = travel, Z = away from the fabric, fabric top at Z = 0.
Unit coordinate u runs along a unit's axis from the motor's gearbox face (u = 0) towards its roller.

Where a value comes from is marked. MEASURED = calipers. PRINTED = printed in crawler v3 on 16 Nov 2026 with
no fault recorded. V4 = drawn for crawler v4 after the v3 print; no print result is on record for it.
ASSUMED = from a datasheet or a typical module drawing, not checked against the part on the bench.
"""

# Magnet and roller
MAG_D = 8.92          # MEASURED N42 rod diameter (Thomas, calipers, 16 Nov 2026)
MAG_L = 25.0          # ASSUMED nominal length; the bore leaves 1.9 slack
BORE_R = 4.6          # V4: 9.2 bore, 0.28 over the magnet (FDM holes print small; v3's 8.2 bore was too tight)
ROLLER_WALL = 1.4     # PRINTED: magnet sits 1.4 + clearance from the fabric
AX = BORE_R + ROLLER_WALL   # roller radius and axis height, 6.0

# N20 gear motor
N20_L = 24.0          # ASSUMED body length, gearbox 9 + can 15
N20_W = 12.0          # ASSUMED body width (Y)
N20_H = 10.0          # ASSUMED body height (Z)
N20_SHAFT_L = 10.0    # ASSUMED D-shaft length
SHAFT_R = 1.55        # PRINTED: 3 mm shaft plus clearance
SHAFT_FLAT = 1.05     # PRINTED: flat sits 1.05 above the axis (2.5 across the D, plus clearance)
TUNNEL_W = 12.2       # PRINTED: press fit for the N20 body
TUNNEL_H = 10.2
TERMINAL_L = 5.4      # V4: space behind the motor for terminals and the cap plug

# Unit layout along u
STOP_WALL = 1.2       # wall the gearbox face sits against
GAP = 0.3             # running clearance at each roller end
HUB_L = 10.4          # PRINTED: D-hole depth in the roller
HUB_FLOOR = 1.1       # solid between the D hole and the magnet bore
BORE_L = 26.9         # V4: magnet 25 + 1.9 for the cap plug
PLUG_L = 1.8          # cap plug that presses into the bore
CAP_L = 5.0           # cap flange, takes the axle screw
END_WALL = 2.5        # wall that carries the axle screw
AXLE_HOLE_R = 1.7     # M3 clearance: the screw turns in this hole
AXLE_PILOT_R = 1.3    # M3 self-taps into the cap
AXLE_PILOT_L = 6.0

# Chassis
AXIS_PITCH = 24.0     # ASSUMED sufficient: Y distance between the two roller axes. Sets how far each magnet
#                       sits from the other unit's steel motor can (13.5 mm surface to surface at 24).
SIDE = 8.0            # chassis material each side of an axis in Y
FLOOR_Z = 0.4         # V4: underside clearance over the fabric
DECK_Z = 14.6         # V4: top of the chassis, 0.8 over the roller
WELL_CLEAR = 0.8      # clearance round the roller inside its well
DECK_T = 1.8          # PRINTED: deck left over the roller
TRAY_SCREW_X = 30.0   # two M3 screws hold the tray, in the solid band between the units
TRAY_SCREW_Y = 2.5    # off centre so the heads clear the board row
TRAY_PILOT_R = 1.3
TRAY_PILOT_L = 8.0
ROW_RIB_HALF = 24.0   # the rib along the board row stops short of the tray screw heads

# Electronics tray (all module sizes ASSUMED from typical drawings; measure the boards he has)
TRAY_T = 1.6
RIM_T = 1.2
RIM_H = 6.0
RIB_H = 2.5
RIB_T = 1.0
FIT = 0.3             # clearance round each board
MCU = (22.5, 18.0)    # ASSUMED ESP32-C3 SuperMini outline
DRIVER = (18.5, 16.0)  # ASSUMED DRV8833 breakout outline
IMU = (21.0, 15.6)    # ASSUMED GY-521 (MPU6050) outline
BATTERY = (30.0, 12.0, 4.0)  # ASSUMED 401230 LiPo, about 110 mAh
USB_NOTCH_W = 10.0
WIRE_NOTCH_W = 6.0

# Derived
U_ROLLER0 = STOP_WALL + GAP                       # roller starts
U_BORE0 = U_ROLLER0 + HUB_L + HUB_FLOOR           # magnet bore starts
U_BODY1 = U_BORE0 + BORE_L                        # roller body ends, cap flange starts
U_CAP1 = U_BODY1 + CAP_L                          # roller ends
U_WALL0 = U_CAP1 + GAP                            # end wall starts
U_WALL1 = U_WALL0 + END_WALL                      # unit ends on the roller side
U_REAR = -(N20_L + TERMINAL_L)                    # unit ends on the motor side
X0 = (U_WALL1 + U_REAR) / 2                       # gearbox face offset that centres the unit on X = 0
HALF_X = (U_WALL1 - U_REAR) / 2                   # chassis half length in X
YA = AXIS_PITCH / 2                               # axis offset in Y
HALF_Y = YA + SIDE                                # chassis half depth in Y
TRAY_Z0 = DECK_Z
TRAY_Z1 = TRAY_Z0 + TRAY_T
SIGNS = (1, -1)                                   # +1 front unit (roller on -X), -1 back unit


def ux(s, u):
    """World X of unit coordinate u for unit s."""
    return s * (X0 - u)


def _cylu(k, s, u0, u1, z, r):
    a, b = sorted((ux(s, u0), ux(s, u1)))
    return k.cylx(a, b, s * YA, z, r)


def _boxu(k, s, u0, u1, dy0, dy1, z0, z1):
    a, b = sorted((ux(s, u0), ux(s, u1)))
    c, d = sorted((s * YA + dy0, s * YA + dy1))
    return k.box(a, b, c, d, z0, z1)


def _dhole(k, s, u0, u1):
    """D-shaft hole from u0 to u1: round hole less the segment above the flat."""
    return k.D(_cylu(k, s, u0 - 0.1, u1, AX, SHAFT_R),
               _boxu(k, s, u0 - 1, u1 + 1, -2, 2, AX + SHAFT_FLAT, AX + 2))


def roller_body(k, s=1):
    r = _cylu(k, s, U_ROLLER0, U_BODY1, AX, AX)
    r = k.D(r, _dhole(k, s, U_ROLLER0, U_ROLLER0 + HUB_L))
    return k.D(r, _cylu(k, s, U_BORE0, U_BODY1 + 0.1, AX, BORE_R))


def roller_cap(k, s=1):
    c = k.U(_cylu(k, s, U_BODY1, U_CAP1, AX, AX), _cylu(k, s, U_BODY1 - PLUG_L, U_BODY1 + 0.1, AX, BORE_R - 0.1))
    return k.D(c, _cylu(k, s, U_CAP1 - AXLE_PILOT_L, U_CAP1 + 0.1, AX, AXLE_PILOT_R))


def chassis(k):
    ch = k.box(-HALF_X, HALF_X, -HALF_Y, HALF_Y, FLOOR_Z, DECK_Z)
    for s in SIGNS:
        # roller well: open below and to the outer side, deck left above
        ch = k.D(ch, _boxu(k, s, STOP_WALL, U_WALL0, -(AX + WELL_CLEAR), SIDE + 0.1, FLOOR_Z - 0.1, DECK_Z - DECK_T))
        # N20 tunnel: closed below, open at the outer end for the cap
        ch = k.D(ch, _boxu(k, s, U_REAR - 0.3, 0, -TUNNEL_W / 2, TUNNEL_W / 2, AX - TUNNEL_H / 2, AX + TUNNEL_H / 2))
        # shaft and gearbox boss through the stop wall
        ch = k.D(ch, _cylu(k, s, -0.2, STOP_WALL + 0.2, AX, 2.6))
        # axle screw through the end wall
        ch = k.D(ch, _cylu(k, s, U_WALL0 - 0.2, U_WALL1 + 0.2, AX, AXLE_HOLE_R))
        # tray screw pilot
        ch = k.D(ch, k.cylz(s * TRAY_SCREW_X, TRAY_SCREW_Y, DECK_Z - TRAY_PILOT_L, DECK_Z + 0.1, TRAY_PILOT_R))
    return ch


def motor_cap(k, s=1):
    """Cover for the open end of an N20 tunnel: plug into the tunnel, flange over the end face, slot for
    the two motor wires. Same shape as the v4 cap."""
    c = _boxu(k, s, U_REAR - 1.6, U_REAR, -SIDE, SIDE, FLOOR_Z, DECK_Z)
    c = k.U(c, _boxu(k, s, U_REAR, U_REAR + 3, -(TUNNEL_W / 2 - 0.1), TUNNEL_W / 2 - 0.1,
                     AX - TUNNEL_H / 2 + 0.1, AX + TUNNEL_H / 2 - 0.1))
    return k.D(c, _boxu(k, s, U_REAR - 2, U_REAR + 3.5, -3, 3, AX + 2.5, AX + 4.2))


def tray_layout():
    """Board pockets on the tray floor as name -> (x0, x1, y0, y1). Boards in a row along -Y, battery along +Y,
    the tray screws in the band between."""
    ix, iy = HALF_X - RIM_T, HALF_Y - RIM_T
    y0 = -iy + 0.2
    x = -ix + 0.2
    out = {}
    for name, (w, d) in (("mcu", MCU), ("driver", DRIVER), ("imu", IMU)):
        out[name] = (x, x + w + FIT, y0, y0 + d + FIT)
        x += w + FIT + RIB_T + 1.0
    bw, bd = BATTERY[0] + FIT, BATTERY[1] + FIT
    out["battery"] = (-bw / 2, bw / 2, iy - 0.2 - bd, iy - 0.2)
    return out


def tray(k):
    """Electronics tray: floor, rim, low ribs that locate each board, notches for USB and motor wires."""
    t = k.box(-HALF_X, HALF_X, -HALF_Y, HALF_Y, TRAY_Z0, TRAY_Z1 + RIM_H)
    t = k.D(t, k.box(-HALF_X + RIM_T, HALF_X - RIM_T, -HALF_Y + RIM_T, HALF_Y - RIM_T, TRAY_Z1, TRAY_Z1 + RIM_H + 0.1))
    lay = tray_layout()
    z0, z1 = TRAY_Z1 - 0.1, TRAY_Z1 + RIB_H
    for name in ("mcu", "driver"):                      # rib after each of the first two boards
        x1, ya, yb = lay[name][1], lay[name][2], lay[name][3]
        t = k.U(t, k.box(x1, x1 + RIB_T, ya, yb, z0, z1))
    row_y1 = max(lay[n][3] for n in ("mcu", "driver", "imu"))
    t = k.U(t, k.box(lay["imu"][1], lay["imu"][1] + RIB_T, lay["imu"][2], lay["imu"][3], z0, z1))
    t = k.U(t, k.box(-ROW_RIB_HALF, ROW_RIB_HALF, row_y1, row_y1 + RIB_T, z0, z1))   # rib along the row, short of the screws
    bx0, bx1, by0, by1 = lay["battery"]
    for x in (bx0 - RIB_T, bx1):                         # battery end ribs
        t = k.U(t, k.box(x, x + RIB_T, by0, by1, z0, z1))
    t = k.U(t, k.box(bx0 - RIB_T, bx1 + RIB_T, by0 - RIB_T, by0, z0, z1))
    # USB-C notch in the -X rim at the MCU, wire notches above each motor cap slot
    ym = (lay["mcu"][2] + lay["mcu"][3]) / 2
    t = k.D(t, k.box(-HALF_X - 0.1, -HALF_X + RIM_T + 0.1, ym - USB_NOTCH_W / 2, ym + USB_NOTCH_W / 2,
                     TRAY_Z1 + 0.6, TRAY_Z1 + RIM_H + 0.1))
    for s in SIGNS:
        xr = ux(s, U_REAR)
        a, b = sorted((xr + s * 0.1, xr - s * (RIM_T + 0.1)))
        t = k.D(t, k.box(a, b, s * YA - WIRE_NOTCH_W / 2, s * YA + WIRE_NOTCH_W / 2, TRAY_Z1 + 2.0, TRAY_Z1 + RIM_H + 0.1))
        t = k.D(t, k.cylz(s * TRAY_SCREW_X, TRAY_SCREW_Y, TRAY_Z0 - 0.1, TRAY_Z1 + 0.1, 1.7))
    return t


def refs(k):
    """Bought parts and the fabric, for the Fusion view and the interference check. Not printed."""
    out = {"Fabric (ref)": k.box(-HALF_X - 15, HALF_X + 15, -HALF_Y - 15, HALF_Y + 15, -1, 0)}
    for s, t in ((1, "front"), (-1, "back")):
        out[f"N20 {t} (ref)"] = k.U(_boxu(k, s, -N20_L, 0, -N20_W / 2, N20_W / 2, AX - N20_H / 2, AX + N20_H / 2),
                                    k.D(_cylu(k, s, 0, N20_SHAFT_L, AX, 1.5),      # D shaft: 3 mm, 2.5 across the flat
                                        _boxu(k, s, -1, N20_SHAFT_L + 1, -2, 2, AX + 1.0, AX + 2)))
        out[f"Magnet in {t} roller (ref)"] = _cylu(k, s, U_BORE0, U_BORE0 + MAG_L, AX, MAG_D / 2)
        out[f"Magnet inside shirt, loose, {t} (ref)"] = _cylu(k, s, U_BORE0, U_BORE0 + MAG_L, -1 - MAG_D / 2, MAG_D / 2)
        out[f"M3 axle screw {t} (ref)"] = _cylu(k, s, U_CAP1 - AXLE_PILOT_L + 0.5, U_WALL1, AX, 1.5)
    lay = tray_layout()
    for name, h in (("mcu", 1.6), ("driver", 1.6), ("imu", 1.6), ("battery", BATTERY[2])):
        x0, x1, y0, y1 = lay[name]
        out[f"{name} (ref)"] = k.box(x0 + FIT / 2, x1 - FIT / 2, y0 + FIT / 2, y1 - FIT / 2, TRAY_Z1, TRAY_Z1 + h)
    return out
