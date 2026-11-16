"""Magnet crawler v4 (16 Nov 2026 12:20): v3 plus measured magnet (8.92 mm, Thomas, calipers), motor covers.
Was v3. Fixes v2: there the fabric was pulled up against the FIXED chassis floor, so the whole
clamp force became sliding drag while the wheels carried almost none of it. Here the outer magnet is itself the driven roller:
the clamp force is the roller's normal force (all traction), and both sides of the fabric only roll, nothing slides.
Two N20s face each other and drive the one roller from both ends (wire one reversed). Straight-line test: no steering.
Frame (mm): X = roller axis, Y = travel, Z = away from fabric, fabric top at Z=0.
"""
AX = 6.0         # roller radius = axis height; magnet wall 1.4 mm round the 9.2 bore
MAG_D = 8.92      # measured by Thomas with calipers, 16 Nov
BORE_R = 4.6      # 9.2 mm bore: 0.28 over the magnet, FDM holes print small
MAG_L = 25.0


def dhole(k, x_open, x_end):
    """3 mm N20 D-shaft hole from x_open to x_end (flat 2.5 across + clearance)."""
    lo, hi = min(x_open, x_end), max(x_open, x_end)
    return k.D(k.cylx(lo - 0.1, hi + 0.1, 0, AX, 1.55), k.box(lo - 1, hi + 1, -2, 2, AX + 1.05, AX + 2))


def roller_body(k):
    r = k.cylx(-24.3, 14.1, 0, AX, AX)
    r = k.D(r, dhole(k, -24.3, -13.9))                                     # 10.4 deep hub
    return k.D(r, k.cylx(-12.8, 14.2, 0, AX, BORE_R))                      # 26.9 deep: magnet 25 + 1.9 slack for the cap


def roller_cap(k):
    c = k.U(k.cylx(14.1, 24.3, 0, AX, AX), k.cylx(12.4, 14.2, 0, AX, BORE_R - 0.1))  # plug presses into the bore
    return k.D(c, dhole(k, 24.3, 14.2))


def chassis(k):
    ch = k.box(-25, 25, -8, 8, 12.8, 14.6)                                  # bridge over the roller (top 12.0)
    ch = k.U(ch, k.box(-4, 4, -18, 18, 12.8, 14.6))
    for s in (-1, 1):
        ch = k.U(ch, k.box(s * 24.6, s * 55.2, -8, 8, 0.4, 14.6))       # floor under the motor; 5.4 past the motor for terminals + cap
        ch = k.D(ch, k.box(s * 25.8, s * 55.5, -6.1, 6.1, AX - 5.1, AX + 5.1))  # N20 tunnel, closed below, open at the outer end for the cap
        ch = k.D(ch, k.cylx(s * 24.4, s * 26, 0, AX, 2.6))                  # shaft and gearbox boss through the stop wall
    for y0, yb in ((-18, -16), (14, 16)):                                    # skids 0.5 off the fabric stop pitching
        ch = k.U(ch, k.box(-2, 2, y0, y0 + 4, 2.5, 13.5))
        ch = k.U(ch, k.sph(0, yb, 2.5, 2.0))
    return ch


def motor_cap(k):
    """Snap-in cover for the outer end of each N20 tunnel: plug into the 12.2 x 10.2 tunnel, flange over the block end,
    slot for the two motor wires. Print flange down, one per side (identical)."""
    c = k.box(0, 1.6, -8, 8, 0.4, 14.6)                                     # flange = block end face
    c = k.U(c, k.box(-3, 0, -6.0, 6.0, AX - 5.0, AX + 5.0))                 # plug, 0.1 per side clearance
    return k.D(c, k.box(-3.5, 2, -3, 3, AX + 2.5, AX + 4.2))                 # wire slot through plug and flange


def refs(k):
    out = {"Magnet in roller (ref)": k.cylx(-12.8, 12.2, 0, AX, MAG_D / 2),
           "Magnet inside shirt, loose (ref)": k.cylx(-12.5, 12.5, 0, -1 - MAG_D / 2, MAG_D / 2),
           "Fabric (ref)": k.box(-60, 60, -30, 30, -1, 0)}
    for s, t in ((-1, "L"), (1, "R")):
        out["N20 " + t + " (ref)"] = k.U(k.box(s * 25.8, s * 49.8, -6, 6, AX - 5, AX + 5), k.cylx(s * 15.8, s * 25.8, 0, AX, 1.5))
    return out
