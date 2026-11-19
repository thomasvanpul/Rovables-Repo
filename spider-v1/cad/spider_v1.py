"""Spider bot v1 (19 Nov 2026, evening). Everything on top, only magnets underneath.

Changes from v0 (Thomas 18:14-18:17: "underneath should just be the magnets", "everything really miniature
and insanely well designed, with space for the vibration and sound and screen", "as small as we can get"):
- The follower frame is gone. Under the leather are two loose pills, two 10 x 4 discs each.
- The chassis is a tray: motor-and-roller units drop in from ABOVE and sit on a 0.8 mm floor. The magnets pull
  the rollers down, so that load goes into the printed floor instead of a screwed strap (v0 needed 3 x M2).
- A gearbox stop wall with a shaft slot keeps each motor from sliding toward its roller.
- A clip-on hat closes the top and carries the bay: 0.96" I2C OLED (27.3 x 27.8 PCB), a 1510 micro speaker
  (15 x 10 x 3.5) behind a grille, and a 10 mm coin vibration motor (2.7 thick). The tether leaves its back.
- Roller wall 1.0 (v0 1.4, PRINTED), tail pocket 3.0 (v0 5.4: solder the wires flat on the tabs).

Axes: X along the bot, Y across, Z up from the leather (Z = 0). Rollers turn about X, so the bot drives along Y.
Two N20s side by side pointing opposite ways; roller A at +X on line +Y, roller B at -X on line -Y.
"""
import json, os, sys
import numpy as np
import manifold3d as m3
import trimesh

M = m3.Manifold
SEG = 96

# magnets: N42 10 x 4 discs, 2 per roller and 2 per pill (ASSUMED nominal until the coupon)
MAG_D, MAG_T, N_STACK = 10.0, 4.0, 2
BORE_R = 5.15
WALL = 1.0                    # roller wall; coupon prints 1.0 to check it holds
R_ROLL = BORE_R + WALL        # 6.15
TYRE = 0.3
AXZ = R_ROLL + TYRE           # 6.45

# N20 (ASSUMED body, PRINTED fits)
N20_L, N20_W, N20_H = 24.0, 12.0, 10.0
TUN_W, TUN_H = 12.5, 10.2      # v1.1: 12.2 (the v3 rig press fit) was too tight in the open-top tray (Thomas 19 Nov 19:20)
SHAFT_R, SHAFT_FLAT, SHAFT_L = 1.55, 1.05, 10.0
SHAFT_ROUND = 4.0             # MEASURED (Thomas 19:20): the flat runs only the outer 6 mm; the 4 mm by the gearbox is full round
ROUND_L = 3.0                 # so the hub entrance is a full circle this deep, then the D
TAIL = 3.0                    # kept at 3.0 so the printed v1 hat still fits the v1.1 tray
STOP_T = 1.2                  # wall the gearbox face sits against
WIRE_W = 3.0                  # v1.1 wire groove across the spine and out of the -Y wall
SLOT_R = 2.0                  # shaft slot in the stop wall, open at the top
BOSS_R, BOSS_D = 2.6, 0.6     # recess for the bearing boss on the gearbox face (ASSUMED ~4.5-5 mm across)

# roller along u from the gearbox face
GAP = 0.3
U_R0 = STOP_T + GAP           # roller starts after the stop wall
HUB_L = SHAFT_L - U_R0 + 0.2  # D hole covers the rest of the shaft plus 0.2
HUB_FLOOR = 0.8
PLUG_L, LID_T = 1.0, 0.6      # lid: 1.0 plug into the bore, 0.6 flange
BORE_L = MAG_T * N_STACK + PLUG_L + 0.2
U_BORE0 = U_R0 + HUB_L + HUB_FLOOR
U_BORE1 = U_BORE0 + BORE_L
U_R1 = U_BORE1 + LID_T
ROLL_LEN = U_BORE1 - U_R0

# tray
PITCH = 14.0
YA = PITCH / 2
CLR = 0.5
SIDE_T = 1.0
END_T = 0.8
FLOOR_T = 0.8
WELL_R = R_ROLL + TYRE + CLR
Z_BOT = AXZ - TUN_H / 2 - FLOOR_T            # underside of the motor floor
TRAY_TOP = AXZ + WELL_R                       # just over the rollers
A_END = U_R1 + CLR + END_T
B_END = N20_L + TAIL + END_T
L_HALF = (A_END + B_END) / 2
XF = L_HALF - A_END                           # gearbox face of motor A at +XF
W_HALF = max(YA + TUN_W / 2 + SIDE_T, YA + WELL_R + SIDE_T)

# hat
HAT_FLOOR = 0.8
BAY_H = 4.2                   # OLED module ~3.7 incl. glass and header stubs bent flat
HAT_TOP = 0.8
LIP_H, LIP_T, LIP_FIT = 1.6, 0.8, 0.1
OLED = (27.3, 27.8)           # PCB outline, ASSUMED typical SSD1306 0.96" module
OLED_WIN = (23.0, 12.5)       # active area window, glass offset toward one edge on most modules: ASSUMED centred
SPK = (15.2, 10.2, 3.6)       # 1510 micro speaker
VIB = (10.2, 2.9)             # coin vibration motor


def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, seg=SEG):
    return M.cylinder(x1 - x0, r, r, seg).rotate([0, 90, 0]).translate([x0, y, z])


def cyl_z(r, x, y, z0, z1, seg=SEG):
    return M.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


UNITS = ((1, YA), (-1, -YA))


def ux(sign, u):
    """Bot X of a point u along motor `sign`'s axis from its gearbox face (u > 0 toward its roller)."""
    return sign * (XF + u)


def span(sign, u0, u1):
    a, b = ux(sign, u0), ux(sign, u1)
    return min(a, b), max(a, b)


# ---------------- rollers and pills ----------------
def roller_local():
    body = M.cylinder(ROLL_LEN, R_ROLL, R_ROLL, SEG)
    d = M.cylinder(HUB_L, SHAFT_R, SHAFT_R, SEG) - M.cube([10, 10, HUB_L - ROUND_L]).translate([-5, SHAFT_FLAT, ROUND_L])
    bore = M.cylinder(BORE_L + 1, BORE_R, BORE_R, SEG).translate([0, 0, HUB_L + HUB_FLOOR])
    lead = M.cylinder(0.5, BORE_R, BORE_R + 0.35, SEG).translate([0, 0, ROLL_LEN - 0.5])
    # 0.4 chamfer on the hub end so it starts on the shaft square
    return body - d - bore - lead


def lid_local():
    return M.cylinder(LID_T, R_ROLL, R_ROLL, SEG) + M.cylinder(PLUG_L, BORE_R - 0.05, BORE_R - 0.05, SEG).translate([0, 0, LID_T])


PILL_END = 0.8
PILL_LEN = PILL_END + BORE_L + LID_T
CH = 0.6


def chamfered_cyl(h, r, c):
    return (M.cylinder(c, r - c, r, SEG) + M.cylinder(h - 2 * c, r, r, SEG).translate([0, 0, c])
            + M.cylinder(c, r, r - c, SEG).translate([0, 0, h - c]))


def pill_local():
    body = chamfered_cyl(PILL_LEN - LID_T, R_ROLL, CH)
    # top chamfer would be where the lid meets it: keep that end square
    body = M.cylinder(CH, R_ROLL - CH, R_ROLL, SEG) + M.cylinder(PILL_LEN - LID_T - CH, R_ROLL, R_ROLL, SEG).translate([0, 0, CH])
    bore = M.cylinder(BORE_L + 1, BORE_R, BORE_R, SEG).translate([0, 0, PILL_END])
    return body - bore


def pill_lid_local():
    flange = M.cylinder(LID_T - 0.0, R_ROLL - 0.0, R_ROLL - 0.0, SEG)
    flange = M.cylinder(LID_T, R_ROLL, R_ROLL - min(CH, LID_T * 0.9), SEG)  # chamfered outer edge
    return flange + M.cylinder(PLUG_L, BORE_R - 0.05, BORE_R - 0.05, SEG).translate([0, 0, LID_T])


# ---------------- tray ----------------
def tray():
    t = box(-L_HALF, L_HALF, -W_HALF, W_HALF, Z_BOT, TRAY_TOP)
    for sign, y in UNITS:
        # motor channel (open at the top) with tail pocket
        x0, x1 = span(sign, -(N20_L + TAIL), 0)
        t = t - box(x0, x1, y - TUN_W / 2, y + TUN_W / 2, AXZ - TUN_H / 2, TRAY_TOP + 1)
        # roller well: open at the top, slot through the floor so the roller reaches the leather
        x0, x1 = span(sign, U_R0 - CLR, U_R1 + CLR)
        t = t - box(x0, x1, y - WELL_R, y + WELL_R, AXZ, TRAY_TOP + 1)
        t = t - cyl_x(WELL_R, x0, x1, y, AXZ)
        t = t - box(x0, x1, y - 3.6, y + 3.6, Z_BOT - 1, AXZ)   # floor slot: roller pokes through
        # shaft slot in the stop wall (open at the top)
        sx0, sx1 = span(sign, -0.01, STOP_T + 0.01)
        t = t - cyl_x(SLOT_R, sx0, sx1, y, AXZ)
        t = t - box(sx0, sx1, y - SLOT_R, y + SLOT_R, AXZ, TRAY_TOP + 1)
        bx0, bx1 = span(sign, -0.01, BOSS_D)
        t = t - cyl_x(BOSS_R, bx0, bx1, y, AXZ)
        t = t - box(bx0, bx1, y - BOSS_R, y + BOSS_R, AXZ, TRAY_TOP + 1)
    # v1.1 wiring (Thomas 19:25: v1 had no route for the N20 wires): each motor's wires rise out of its tail
    # pocket, run forward in the ~1.9 mm between the can top and the tray top, and cross to the -Y wall
    # through a groove over the centre spine; they leave under the hat's tether notch.
    t = t - box(-WIRE_W / 2, WIRE_W / 2, -W_HALF - 1, YA - TUN_W / 2 + 0.5, AXZ + N20_H / 2 + 0.2, TRAY_TOP + 1)
    # hat locating: the hat's lip drops inside the tray walls; four snap dimples on the long walls
    for x in (-L_HALF / 2, L_HALF / 2):
        for y in (-W_HALF, W_HALF):
            t = t - cyl_x(0.5, x - 2, x + 2, y + (0.0 if y > 0 else 0.0) - (SIDE_T - 0.4 if y > 0 else -(SIDE_T - 0.4)), TRAY_TOP - 0.8, 24) if False else t
    return t


SKIRT_T, SKIRT_H, SKIRT_CLR = 0.8, 2.0, 0.05


OLED_X = L_HALF + SKIRT_CLR - OLED[0] / 2 - 0.3
SPK_X = -L_HALF - SKIRT_CLR + SPK[0] / 2 + 0.6
SPK_Y, VIB_Y = 6.5, -8.0


def hat():
    """Lid: top plate (screen window, speaker grille) on walls whose skirt slides 2 mm down over the OUTSIDE
    of the tray (0.05 clearance, snug). Nothing hangs inside, so the bay parts press into their pockets from
    below without passing anything. (Draft 1 had a closed bay; draft 2 had inner lips that blocked the OLED.)"""
    z0 = TRAY_TOP
    ztop = z0 + BAY_H
    ox_, oy_ = L_HALF + SKIRT_CLR + SKIRT_T, W_HALF + SKIRT_CLR + SKIRT_T
    ix_, iy_ = L_HALF + SKIRT_CLR, W_HALF + SKIRT_CLR
    h = box(-ox_, ox_, -oy_, oy_, z0 - SKIRT_H, ztop + HAT_TOP) - box(-ix_, ix_, -iy_, iy_, z0 - SKIRT_H - 1, ztop)
    ox = OLED_X
    sx = SPK_X
    def ring(x0, x1, y0, y1, depth=1.5, t=0.7):
        return box(x0 - t, x1 + t, y0 - t, y1 + t, ztop - depth, ztop) - box(x0, x1, y0, y1, ztop - depth - 1, ztop + 1)
    h = h + ring(ox - OLED[0] / 2, ox + OLED[0] / 2, -OLED[1] / 2, OLED[1] / 2)
    h = h + ring(sx - SPK[0] / 2, sx + SPK[0] / 2, SPK_Y - SPK[1] / 2, SPK_Y + SPK[1] / 2)
    h = h + (cyl_z(VIB[0] / 2 + 0.7, sx, VIB_Y, ztop - 1.5, ztop) - cyl_z(VIB[0] / 2, sx, VIB_Y, ztop - 3, ztop + 1))
    h = h - box(-ox_ - 1, ox_ + 1, -oy_ - 1, oy_ + 1, ztop + HAT_TOP, 99)
    h = h ^ box(-ox_, ox_, -oy_, oy_, -99, 99)
    h = h - box(ox - OLED_WIN[0] / 2, ox + OLED_WIN[0] / 2, -OLED_WIN[1] / 2, OLED_WIN[1] / 2, ztop - 0.1, ztop + HAT_TOP + 0.1)
    for i in range(-2, 3):
        for j in range(-1, 2):
            h = h - cyl_z(0.6, sx + i * 2.4, SPK_Y + j * 2.4, ztop - 0.1, ztop + HAT_TOP + 0.1, 16)
    # tether notch in the skirt and wall at the -Y side, centre
    h = h - box(-3.0, 3.0, -oy_ - 1, -iy_ + 0.1, z0 - SKIRT_H - 1, z0 + 2.4)
    return h


# bay layout: OLED at +X, speaker and coin motor at -X, all hung under the top plate
# bay contents (bought, for the clash check and the render)
def bay_parts():
    z0 = TRAY_TOP
    ox, sx = OLED_X, SPK_X
    return {
        "oled": box(ox - OLED[0] / 2, ox + OLED[0] / 2, -OLED[1] / 2, OLED[1] / 2, z0 + BAY_H - 3.7, z0 + BAY_H),
        "speaker": box(sx - SPK[0] / 2, sx + SPK[0] / 2, SPK_Y - SPK[1] / 2, SPK_Y + SPK[1] / 2, z0 + BAY_H - SPK[2], z0 + BAY_H),
        "vibration": cyl_z(VIB[0] / 2, sx, VIB_Y, z0 + BAY_H - VIB[1], z0 + BAY_H),
    }


def bought(sign, y):
    x0, x1 = span(sign, -N20_L, 0)
    out = {"n20": box(x0, x1, y - N20_W / 2, y + N20_W / 2, AXZ - N20_H / 2, AXZ + N20_H / 2)}
    s0, s1 = span(sign, 0, SHAFT_L)
    out["shaft"] = cyl_x(1.5, s0, s1, y, AXZ)
    m0, m1 = span(sign, U_BORE0, U_BORE0 + MAG_T * N_STACK)
    out["mag"] = cyl_x(MAG_D / 2, m0, m1, y, AXZ)
    return out


def place_axial(part_local, sign, y, u0, z=AXZ):
    """Part drawn along +Z from 0; put it on motor `sign`'s axis starting at u0, pointing away from the motor."""
    p = part_local.rotate([0, 90, 0])
    if sign < 0:
        p = p.rotate([0, 0, 180])
    return p.translate([ux(sign, u0), y, z])


def coupon():
    parts = []
    for i, r in enumerate((5.05, 5.10, 5.15, 5.20)):
        ring = M.cylinder(4.5, r + WALL, r + WALL, SEG) - M.cylinder(5, r, r, SEG).translate([0, 0, -0.2])
        parts.append(ring.translate([i * 15.0, 0, 0]))
    hole = M.cylinder(8.7, SHAFT_R, SHAFT_R, SEG) - M.cube([10, 10, 8.7 - ROUND_L]).translate([-5, SHAFT_FLAT, ROUND_L])
    d = M.cylinder(8.7, 3.5, 3.5, SEG) - hole.translate([0, 0, 0])
    parts.append(d.translate([0, 15, 0]))
    for i, w in enumerate((12.3, 12.5, 12.7)):   # N20 channel widths: which one the motor pushes into
        t = box(0, w + 2.0, 0, 5, 0, 7.0) - box(1.0, 1.0 + w, -1, 6, 0.8, 20)
        parts.append(t.translate([8 + i * 16.5, 12, 0]))
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def tm(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)


def main(out):
    os.makedirs(out + "/stl", exist_ok=True)
    os.makedirs(out + "/assy", exist_ok=True)
    tr, ht = tray(), hat()
    rl, ld, pl, pld, cp = roller_local(), lid_local(), pill_local(), pill_lid_local(), coupon()
    assy = {"tray": tr, "hat": ht}
    buy = {}
    LEATHER = 1.8
    for sign, y in UNITS:
        k = "A" if sign > 0 else "B"
        assy["roller" + k] = place_axial(rl, sign, y, U_R0)
        assy["lid" + k] = place_axial(ld.rotate([180, 0, 0]).translate([0, 0, LID_T]), sign, y, U_BORE1)
        b = bought(sign, y)
        for n, v in b.items():
            buy[n + k] = v
        # pill under the leather, under the driven magnets
        mc = U_BORE0 + MAG_T * N_STACK / 2
        pc = PILL_END + MAG_T * N_STACK / 2
        zp = -LEATHER - R_ROLL
        assy["pill" + k] = place_axial(pl, sign, y, mc - pc, zp)
        assy["pilllid" + k] = place_axial(pld.rotate([180, 0, 0]).translate([0, 0, LID_T]), sign, y, mc - pc + PILL_LEN - LID_T, zp)
        m0, m1 = span(sign, mc - MAG_T * N_STACK / 2, mc + MAG_T * N_STACK / 2)
        buy["pillmag" + k] = cyl_x(MAG_D / 2, m0, m1, y, zp)
    buy.update(bay_parts())

    allp = {**assy, **buy}
    names = list(allp)
    ok_pairs = set()
    for k in "AB":
        ok_pairs |= {frozenset(p) for p in [("roller" + k, "shaft" + k), ("lid" + k, "roller" + k), ("roller" + k, "mag" + k),
                                             ("pill" + k, "pillmag" + k), ("pilllid" + k, "pill" + k), ("tray", "n20" + k)]}
    clashes = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if frozenset((a, b)) in ok_pairs:
                continue
            v = (allp[a] ^ allp[b]).volume()
            if v > 0.05:
                clashes.append((a, b, round(v, 3)))

    def sweep(part, dz, steps=40):
        acc = part
        for i in range(1, steps + 1):
            acc = acc + part.translate([0, 0, dz * i / steps])
        return acc
    order = {}
    for k in "AB":
        unit = buy["n20" + k] + buy["shaft" + k] + assy["roller" + k] + assy["lid" + k]
        order[f"unit_{k}_drops_in_from_above_mm3"] = round((sweep(unit, 40) ^ tr).volume(), 3)
    bay = buy["oled"] + buy["speaker"] + buy["vibration"]
    order["bay_parts_slide_out_of_open_bottom_mm3"] = round((sweep(bay, -12) ^ ht).volume(), 3)
    order["hat_drops_on_from_above_mm3"] = round((sweep(ht, 20) ^ tr).volume(), 3)
    # the magnets' pull goes into the tray floor: is there floor under each motor?
    floor_under = {}
    for k in "AB":
        probe = buy["n20" + k].translate([0, 0, -0.5])
        floor_under[k] = round((probe ^ tr).volume(), 1)
    lowest = {"tray_underside_z": round(tr.bounding_box()[2], 2), "roller_bottom_z": round(assy["rollerA"].bounding_box()[2], 2)}

    # wire routes, 0.9 mm bundle: tail pocket -> up -> along the can top -> across the spine -> out of -Y
    def seg(p, q, t=0.9):
        lo = [min(p[i], q[i]) - t / 2 for i in range(3)]
        hi = [max(p[i], q[i]) + t / 2 for i in range(3)]
        return box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
    zw = AXZ + N20_H / 2 + 0.75
    solid = tr + buy["n20A"] + buy["n20B"] + buy["oled"] + buy["speaker"] + buy["vibration"] + ht
    routes = {}
    for sign, y in UNITS:
        k = "A" if sign > 0 else "B"
        xt = ux(sign, -(N20_L + TAIL / 2))
        pts = [(xt, y, AXZ), (xt, y, zw), (0.0, y, zw), (0.0, -W_HALF - 1.5, zw)]
        routes[k] = round(sum((seg(pts[i], pts[i + 1]) ^ solid).volume() for i in range(len(pts) - 1)), 3)
    rep_routes = routes
    printed = {"tray": tr, "hat": ht, "roller": rl, "roller_lid": ld, "pill": pl, "pill_lid": pld, "fit_coupon": cp}
    parts = {n: {"watertight": bool(tm(p).is_watertight), "bodies": len(tm(p).split(only_watertight=False)),
                 "bbox": [round(v, 2) for v in tm(p).extents], "vol": round(p.volume(), 1)} for n, p in printed.items()}
    size = {"L_with_hat": round(2 * (L_HALF + SKIRT_CLR + SKIRT_T), 2), "W_with_hat": round(2 * (W_HALF + SKIRT_CLR + SKIRT_T), 2), "L": round(2 * L_HALF, 2), "W": round(2 * W_HALF, 2), "tray_H": round(TRAY_TOP - Z_BOT + 0.0, 2),
            "H_with_hat_above_leather": round(TRAY_TOP + BAY_H + HAT_TOP, 2), "axis_z": AXZ,
            "pill": [round(2 * R_ROLL, 2), round(PILL_LEN, 2)], "roller": [round(2 * R_ROLL, 2), round(ROLL_LEN + LID_T, 2)]}
    rep = {"wire_routes_through_solid_mm3": rep_routes, "size": size, "clashes": clashes, "assembly_order": order, "floor_under_motor_mm3": floor_under, "lowest": lowest, "parts": parts}

    # export in print orientation
    def ex(m, n):
        t = tm(m)
        lo, hi = t.bounds
        t.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        t.export(f"{out}/stl/{n}.stl")
    ex(tr, "tray")                                   # floor down
    ex(ht.rotate([180, 0, 0]), "hat")                # top face down, bay open upward
    ex(rl, "roller_x2")
    ex(ld, "roller_lid_x2")
    ex(pl, "pill_x2")
    ex(pld, "pill_lid_x2")
    ex(cp, "fit_coupon")
    for n, p in allp.items():
        tm(p).export(f"{out}/assy/{n}.stl")
    leather = trimesh.creation.box([2 * L_HALF + 24, 2 * W_HALF + 24, LEATHER])
    leather.apply_translation([0, 0, -LEATHER / 2])
    leather.export(f"{out}/assy/leather.stl")
    json.dump(rep, open(f"{out}/checks.json", "w"), indent=1)
    return rep


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1] if len(sys.argv) > 1 else "out"), indent=1))
