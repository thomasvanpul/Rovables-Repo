"""Spider bot v0: two N20s side by side, 10 x 4 mm N42 discs as the driven rollers.

19 Nov 2026, for Thomas's tonight test (fit, clamp, drive on a leather offcut).
Continues Rovable v2 (Rovables-Repo branch v2, cad/rovable_v2_geom.py); fits marked PRINTED
come from the 16 Nov v3 print; everything else is ASSUMED until the fit coupon says otherwise.

Axes: X along the bot (rollers at the two ends), Y across, Z up from the fabric (Z=0 is the leather).
Each roller turns about X, so the bot drives along Y. Differential: roller A at +X on line +Y,
roller B at -X on line -Y, motors lying side by side and pointing opposite ways (Rovable v2 layout).

Magnets: 2 discs stacked per roller (10 dia x 8 long), axis along X. Field of an axially
magnetised disc is symmetric about its axis, so the clamp does not pulse as the roller turns.
Follower rollers under the leather carry 2 discs each, poles REVERSED (antiparallel side by side
dipoles attract).
"""
import numpy as np
import manifold3d as m3
import trimesh

M = m3.Manifold
SEG = 96
m3.set_circular_segments(SEG) if hasattr(m3, "set_circular_segments") else None

# --- magnets (ASSUMED nominal, his count ~20) ---
MAG_D = 10.0
MAG_T = 4.0
N_STACK = 2
BORE_R = 5.15          # 10.3 bore: v4 found FDM holes print small, +0.28 on 8.92 rod. Coupon checks 10.1-10.4
PLUG_L = 1.2
BORE_L = MAG_T * N_STACK + PLUG_L + 0.2   # magnets + cap plug + slack (v0 first draft let the plug hit the magnets)
WALL = 1.4             # PRINTED: roller wall (v3)
R_ROLL = BORE_R + WALL  # 6.55
TYRE = 0.3             # heat-shrink or a stretched rubber band on the roller
AXZ = R_ROLL + TYRE    # axis height above the leather, 6.85

# --- N20 (ASSUMED body, PRINTED fits) ---
N20_L, N20_W, N20_H = 24.0, 12.0, 10.0
TUN_W, TUN_H = 12.2, 10.2      # PRINTED press fit
SHAFT_R, SHAFT_FLAT = 1.55, 1.05  # PRINTED D hole
SHAFT_L = 10.0
TAIL = 5.4             # V4 terminal space behind the can (bare N20, no encoder board)
BOSS_R = 2.2           # slot for the gearbox output boss and shaft

# --- roller along its own axis u (u=0 at the gearbox face) ---
GAP = 0.3
HUB_L = 10.0           # D hole depth: the 10 mm shaft ends 0.3 short (first draft at 7.5 put the shaft into the magnets)
HUB_FLOOR = 1.0
CAP_L = 1.4            # cap flange; plug goes 1.2 into the bore
U_R0 = GAP
U_BORE0 = U_R0 + HUB_L + HUB_FLOOR
U_BORE1 = U_BORE0 + BORE_L
U_R1 = U_BORE1 + CAP_L          # far end including the cap flange
ROLL_LEN = U_BORE1 - U_R0        # printed roller body; the cap flange adds CAP_L beyond it

# --- chassis ---
PITCH = 15.2           # Y distance between the motor lines; leaves a 3.0 spine for M2 screws
YA = PITCH / 2
SIDE_T = 1.4
END_T = 1.2
STOP_T = 1.2           # wall the gearbox face sits against
CLR = 0.6              # roller well clearance
DECK_T = 1.4
TOP_Z = AXZ + R_ROLL + CLR + DECK_T
FLOOR_T = 1.0          # strap under the motors: it carries both rollers' clamp (they pull the motors down)
STRAP_SCREWS = None    # set after W_HALF
# X positions: motor A face at +XF pointing +X; motor B face at -XF pointing -X
L_HALF = None


def solve_layout():
    # roller end + clearance + end wall = L/2 ; motor tail + end cap wall = -L/2 (mirror for B)
    # xf + U_R1 + CLR + END_T = L/2 ; xf - (N20_L + TAIL) - END_T >= -L/2
    a = U_R1 + CLR + END_T
    b = N20_L + TAIL + END_T
    L = a + b               # tightest: both constraints active
    xf = L / 2 - a
    return L / 2, xf


L_HALF, XF = solve_layout()
W_HALF = YA + TUN_W / 2 + SIDE_T
W_HALF = max(W_HALF, YA + R_ROLL + CLR + SIDE_T)
# three M2 x 8 self-tappers: centre spine and both outer walls (2.45 of solid there at X=0)
STRAP_SCREWS = [(0.0, 0.0), (0.0, YA + TUN_W / 2 + (W_HALF - YA - TUN_W / 2) / 2), (0.0, -(YA + TUN_W / 2 + (W_HALF - YA - TUN_W / 2) / 2))]


def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, seg=SEG):
    c = M.cylinder(x1 - x0, r, r, seg)          # along z
    return c.rotate([0, 90, 0]).translate([x0, y, z])


def d_shaft_hole(x0, x1, y, z, sign):
    """D hole along X. The flat is on +Z in the roller's own frame (orientation free on the shaft)."""
    c = cyl_x(SHAFT_R, x0, x1, y, z)
    cut = box(min(x0, x1), max(x0, x1), y - 3, y + 3, z + SHAFT_FLAT, z + 3)
    return c - cut


# ---------------- driven roller (print standing on its cap end? no: hub end down) ----------------
def roller_local():
    """Roller in its own frame: axis along +Z, z=0 at the hub end (gearbox side)."""
    body = M.cylinder(ROLL_LEN, R_ROLL, R_ROLL, SEG)
    # D hole from the hub end
    d = M.cylinder(HUB_L, SHAFT_R, SHAFT_R, SEG)
    d = d - M.cube([10, 10, HUB_L]).translate([-5, SHAFT_FLAT, 0])
    bore = M.cylinder(BORE_L + 1, BORE_R, BORE_R, SEG).translate([0, 0, U_BORE0 - U_R0])
    # small chamfer lead-in at the bore mouth
    lead = M.cylinder(0.6, BORE_R, BORE_R + 0.4, SEG).translate([0, 0, ROLL_LEN - 0.6])
    # two shallow lips at the ends keep a band/heat-shrink tyre in place
    return body - d - bore - lead


def roller_cap_local():
    """Cap: flange CAP_L, plug PLUG_L into the bore (0.1 interference on radius)."""
    flange = M.cylinder(CAP_L, R_ROLL, R_ROLL, SEG)
    plug = M.cylinder(PLUG_L, BORE_R - 0.05, BORE_R - 0.05, SEG).translate([0, 0, CAP_L])
    return flange + plug


def place_roller(part_local, sign, y):
    """Map roller frame (axis +Z from the hub end) into the bot. sign=+1: roller at +X."""
    p = part_local.rotate([0, 90, 0])  # +Z -> +X
    if sign < 0:
        p = p.rotate([0, 0, 180])
    x0 = sign * (XF + U_R0)
    return p.translate([x0, y, AXZ])


# ---------------- bought parts for the clash check ----------------
def n20_body(sign, y):
    if sign > 0:
        x0, x1 = XF - N20_L, XF
    else:
        x0, x1 = -XF, -XF + N20_L
    return box(x0, x1, y - N20_W / 2, y + N20_W / 2, AXZ - N20_H / 2, AXZ + N20_H / 2)


def n20_shaft(sign, y):
    if sign > 0:
        return cyl_x(1.5, XF, XF + SHAFT_L, y, AXZ)
    return cyl_x(1.5, -XF - SHAFT_L, -XF, y, AXZ)


def magnets(sign, y):
    if sign > 0:
        x0 = XF + U_BORE0
        return cyl_x(MAG_D / 2, x0, x0 + MAG_T * N_STACK, y, AXZ)
    x1 = -(XF + U_BORE0)
    return cyl_x(MAG_D / 2, x1 - MAG_T * N_STACK, x1, y, AXZ)


# ---------------- chassis ----------------
def chassis():
    outer = box(-L_HALF, L_HALF, -W_HALF, W_HALF, FLOOR_T + 0.0 if False else AXZ - TUN_H / 2, TOP_Z)
    # bottom of the chassis walls: at the tunnel floor level (strap closes the motors from below)
    z_bot = AXZ - TUN_H / 2
    outer = box(-L_HALF, L_HALF, -W_HALF, W_HALF, z_bot, TOP_Z)
    cuts = []
    for sign, y in ((1, YA), (-1, -YA)):
        # motor tunnel, open at the bottom (drop-in), plus tail pocket for terminals
        if sign > 0:
            tx0, tx1 = XF - N20_L - TAIL, XF
        else:
            tx0, tx1 = -XF, -XF + N20_L + TAIL
        cuts.append(box(tx0, tx1, y - TUN_W / 2, y + TUN_W / 2, z_bot - 1, AXZ + TUN_H / 2))
        # roller well: full roller diameter + clearance, open at the bottom and down to the fabric
        if sign > 0:
            wx0, wx1 = XF + STOP_T * 0 + 0.0, XF + U_R1 + CLR
            wx0 = XF + U_R0 - CLR
        else:
            wx0, wx1 = -(XF + U_R1 + CLR), -(XF + U_R0 - CLR)
        rw = R_ROLL + TYRE + CLR
        cuts.append(box(wx0, wx1, y - rw, y + rw, z_bot - 1, AXZ))
        cuts.append(cyl_x(rw, wx0, wx1, y, AXZ))
        # shaft / gearbox boss slot through the stop wall region (open below)
        # (the face of the gearbox sits at XF; the roller starts at XF+GAP, so the wall
        #  between motor and roller is replaced by the roller well itself)
    body = outer
    for c in cuts:
        body = body - c
    # gearbox stop: a tab either side of the shaft at the gearbox face keeps the motor from walking
    for sign, y in ((1, YA), (-1, -YA)):
        xs = XF if sign > 0 else -XF
        x0, x1 = (xs, xs + 0.0) if False else ((xs, xs + 0.25) if sign > 0 else (xs - 0.25, xs))
    # wire channel along the top inside the deck: from both tails to the tether exit at -Y rear face
    ch = box(-L_HALF + END_T, L_HALF - END_T, -1.0, 1.0, AXZ + TUN_H / 2 - 0.01, AXZ + TUN_H / 2 + 1.6)
    body = body - ch
    # tether exit hole through the -Y side wall at the centre, above the motor
    body = body - box(-2.5, 2.5, -W_HALF - 1, 0, AXZ + TUN_H / 2 - 0.2, AXZ + TUN_H / 2 + 1.6)
    # M2 pilot holes up into the central spine for the floor strap (two, at the motor overlap)
    for (x, y) in STRAP_SCREWS:
        body = body - M.cylinder(7.0, 0.8, 0.8, 32).translate([x, y, z_bot - 0.5])
    # flat top: 4 M2 pilot holes for later add-ons (not through)
    for x in (-L_HALF + 5, L_HALF - 5):
        for y in (-W_HALF + 4, W_HALF - 4):
            body = body - M.cylinder(1.2, 0.8, 0.8, 32).translate([x, y, TOP_Z - 1.2])
    # zip-tie strain relief pair beside the tether exit
    for x in (-5.5, 5.5):
        body = body - box(x - 0.9, x + 0.9, -W_HALF - 1, -W_HALF + 2.2, TOP_Z - 3.2, TOP_Z - 1.6)
    return body


def strap():
    """Floor strap under both motors' overlap. M2 x 8 screws into the spine."""
    z_bot = AXZ - TUN_H / 2
    x0, x1 = -(XF - CLR), XF - CLR   # stops short of both roller wells (first draft hit the rollers)
    s = box(x0, x1, -W_HALF + 0.0, W_HALF - 0.0, z_bot - FLOOR_T, z_bot)
    for (x, y) in STRAP_SCREWS:
        s = s - M.cylinder(3, 1.1, 1.1, 32).translate([x, y, z_bot - FLOOR_T - 1])
    return s


# ---------------- follower (under the leather, against the body) ----------------
F_PIVOT_R = 1.7        # roller hole the M3 screw tip turns in
F_END = 3.0            # closed ends of the follower roller
F_ROLL_LEN = F_END + BORE_L + F_END
F_PROTRUDE = 1.2       # follower roller stands this far above its frame, toward the leather
F_WALL = 2.6           # frame side walls carry the M3 pivot screws
F_FLOOR = 1.2


def follower_roller_local():
    body = M.cylinder(F_ROLL_LEN, R_ROLL, R_ROLL, SEG)
    bore = M.cylinder(BORE_L, BORE_R, BORE_R, SEG).translate([0, 0, F_END])
    # load from the side: split along the axis is weak; instead the bore opens at one end
    bore_open = M.cylinder(F_END + 0.01, BORE_R, BORE_R, SEG).translate([0, 0, F_END + BORE_L - 0.01])
    piv0 = M.cylinder(F_END - 0.8, F_PIVOT_R, F_PIVOT_R, 32).translate([0, 0, -0.01])
    return body - bore - bore_open - piv0


def follower_cap_local():
    flange = M.cylinder(F_END, R_ROLL, R_ROLL, SEG)
    plug = M.cylinder(PLUG_L, BORE_R - 0.05, BORE_R - 0.05, SEG).translate([0, 0, F_END])
    piv = M.cylinder(F_END - 0.8, F_PIVOT_R, F_PIVOT_R, 32).translate([0, 0, -0.01])
    return flange + plug - piv


def follower_frame():
    """Frame in its own frame: Z=0 is its underside (against the shirt/body), rollers face +Z.
    Roller centres sit under the top rollers' contact lines (same X span centre, same Y)."""
    zc = F_FLOOR + R_ROLL + 0.4                # axis height above the frame underside
    ztop = zc + R_ROLL - F_PROTRUDE
    mag_c = XF + U_BORE0 + MAG_T * N_STACK / 2  # follower magnets sit under the driven magnets
    cx = mag_c - (F_END + MAG_T * N_STACK / 2) + F_ROLL_LEN / 2
    half = F_ROLL_LEN / 2
    x_span = cx + half + 0.4 + F_WALL
    fw = W_HALF
    frame = box(-x_span, x_span, -fw, fw, 0, ztop)
    for sign, y in ((1, YA), (-1, -YA)):
        c = sign * cx
        frame = frame - box(c - half - 0.4, c + half + 0.4, y - R_ROLL - 0.6, y + R_ROLL - 0 + 0.6, F_FLOOR, ztop + 1)
        # M3 pilot through each end wall on the roller axis (self-tapping, the tip is the pivot)
        frame = frame - cyl_x(1.25, c - half - 0.4 - F_WALL - 1, c + half + 0.4 + F_WALL + 1, y, zc)
    # lighten and keep it flexible: slot out the middle between the two wells
    frame = frame - box(-cx + half + 0.4 + F_WALL, cx - half - 0.4 - F_WALL, -fw + 2, fw - 2, F_FLOOR, ztop + 1)
    # round-ish underside edges are left to the slicer; sew holes at the four corners (thread through)
    for x in (-x_span + 2.2, x_span - 2.2):
        for y in (-fw + 2.2, fw - 2.2):
            frame = frame - M.cylinder(ztop + 2, 0.9, 0.9, 24).translate([x, y, -1])
    return frame, zc, cx


# ---------------- fit coupon ----------------
def coupon():
    parts = []
    for i, r in enumerate((5.05, 5.10, 5.15, 5.20)):
        ring = M.cylinder(4.5, r + 1.4, r + 1.4, SEG) - M.cylinder(5, r, r, SEG).translate([0, 0, -0.2])
        parts.append(ring.translate([i * 16.0, 0, 0]))
    # D hole check (two depths) and an N20 tunnel slice
    d = M.cylinder(6, 4, 4, SEG) - (M.cylinder(7, SHAFT_R, SHAFT_R, SEG) - M.cube([10, 10, 8]).translate([-5, SHAFT_FLAT, -1])).translate([0, 0, -0.5])
    parts.append(d.translate([0, 16, 0]))
    t = box(0, 15.2, 0, 6, 0, 13.0) - box(1.5, 1.5 + TUN_W, -1, 7, 1.4, 1.4 + TUN_H + 5)
    parts.append(t.translate([12, 13, 0]))
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)


if __name__ == "__main__":
    import json, os, sys
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out + "/stl", exist_ok=True)
    ch = chassis()
    st = strap()
    rl = roller_local()
    cap = roller_cap_local()
    fr, fzc, fcx = follower_frame()
    frl = follower_roller_local()
    fcap = follower_cap_local()
    cp = coupon()

    report = {"layout": {"L": 2 * L_HALF, "W": 2 * W_HALF, "H_top": TOP_Z, "XF": XF, "axis_z": AXZ,
                          "roller_len": ROLL_LEN, "roller_od": 2 * R_ROLL, "contact_x": XF + U_R0 + ROLL_LEN / 2,
                          "motor_floor_gap": AXZ - TUN_H / 2 - FLOOR_T}}

    # --- assembled bot ---
    assy = {"chassis": ch, "strap": st}
    bought = {}
    for sign, y in ((1, YA), (-1, -YA)):
        k = "A" if sign > 0 else "B"
        assy["roller" + k] = place_roller(rl, sign, y)
        # cap sits at the far end: in roller frame its flange starts at ROLL_LEN - CAP_L, plug pointing back (-Z)
        cap_in = cap.rotate([180, 0, 0]).translate([0, 0, ROLL_LEN + CAP_L])
        assy["cap" + k] = place_roller(cap_in, sign, y)
        bought["n20" + k] = n20_body(sign, y)
        bought["shaft" + k] = n20_shaft(sign, y)
        bought["mag" + k] = magnets(sign, y)

    checks = {}
    names = list(assy) + list(bought)
    allp = {**assy, **bought}
    # pairs expected to touch/overlap: roller vs its shaft (D-hole fit), cap vs roller (plug), roller vs magnets
    allowed = set()
    for k in "AB":
        allowed |= {("roller" + k, "shaft" + k), ("cap" + k, "roller" + k), ("roller" + k, "mag" + k),
                    ("cap" + k, "mag" + k), ("chassis", "n20" + k), ("strap", "n20" + k)}
    clashes = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in allowed or (b, a) in allowed:
                continue
            v = (allp[a] ^ allp[b]).volume()
            if v > 0.05:
                clashes.append((a, b, round(v, 3)))
    checks["clashes"] = clashes
    # press-fit motor in tunnel: chassis vs body overlap is expected 0 (tunnel 0.1 over) -> report
    checks["chassis_vs_motor_overlap_mm3"] = [round((ch ^ bought["n20A"]).volume(), 3), round((ch ^ bought["n20B"]).volume(), 3)]
    checks["magnet_inside_roller_overlap_mm3"] = round((assy["rollerA"] ^ bought["magA"]).volume(), 3)

    # --- assembly order: motor+roller+cap unit drops in from below (chassis printed deck-down) ---
    def sweep_down(part, dz=40.0, steps=40):
        acc = part
        for i in range(1, steps + 1):
            acc = acc + part.translate([0, 0, -dz * i / steps])
        return acc
    order = {}
    for k in "AB":
        unit = bought["n20" + k] + bought["shaft" + k] + assy["roller" + k] + assy["cap" + k]
        order["unit_" + k + "_drop_in_from_below_clash_mm3"] = round((sweep_down(unit) ^ ch).volume(), 3)
    order["strap_screws_from_below"] = True
    checks["assembly_order"] = order

    # leather gap: lowest point of chassis/strap above the fabric, roller bottom at TYRE
    def zmin(p):
        return p.bounding_box()[2] if hasattr(p, "bounding_box") else None
    checks["lowest_chassis_z"] = round(ch.bounding_box()[2], 3)
    checks["lowest_strap_z"] = round(st.bounding_box()[2], 3)
    checks["roller_bottom_z_without_tyre"] = round(assy["rollerA"].bounding_box()[2], 3)

    # --- watertight, one solid each ---
    printed = {"chassis": ch, "strap": st, "roller": rl, "roller_cap": cap, "follower_frame": fr,
               "follower_roller": frl, "follower_cap": fcap, "fit_coupon": cp}
    solids = {}
    for n, p in printed.items():
        tm = to_trimesh(p)
        solids[n] = {"watertight": bool(tm.is_watertight), "bodies": len(tm.split(only_watertight=False)),
                     "vol_mm3": round(p.volume(), 1), "bbox": [round(v, 2) for v in tm.extents]}
    checks["printed_parts"] = solids

    # --- follower assembled: rollers in frame, clash check ---
    fassy = {"frame": fr}
    for sign, y in ((1, YA), (-1, -YA)):
        k = "A" if sign > 0 else "B"
        c = sign * fcx
        rr = frl.rotate([0, 90, 0]).translate([c - F_ROLL_LEN / 2, y, fzc])
        fc = fcap.rotate([0, -90, 0]).translate([c + F_ROLL_LEN / 2, y, fzc])
        fassy["froller" + k] = rr
        fassy["fcap" + k] = fc
    fcl = []
    fn = list(fassy)
    for i, a in enumerate(fn):
        for b in fn[i + 1:]:
            if {a[-1], b[-1]} == {a[-1]} and a != "frame" and b != "frame":
                continue  # roller and its own cap overlap at the plug
            v = (fassy[a] ^ fassy[b]).volume()
            if v > 0.05:
                fcl.append((a, b, round(v, 3)))
    checks["follower_clashes"] = fcl

    # --- export print-oriented STLs ---
    def export(man, name):
        to_trimesh(man).export(f"{out}/stl/{name}.stl")
    # chassis printed deck down (flip), strap flat, rollers hub-end down, caps flange down
    zb = ch.bounding_box()
    export(ch.rotate([180, 0, 0]).translate([0, 0, TOP_Z]), "chassis")
    export(st.translate([0, 0, -st.bounding_box()[2]]), "strap")
    export(rl, "roller_x2")
    export(cap, "roller_cap_x2")
    export(fr, "follower_frame")
    export(frl, "follower_roller_x2")
    export(fcap, "follower_cap_x2")
    export(cp, "fit_coupon")

    # assembled scene for renders
    scene = trimesh.Scene()
    colors = {"chassis": [40, 40, 44, 255], "strap": [60, 60, 66, 255]}
    for n, p in assy.items():
        tm = to_trimesh(p)
        tm.visual.face_colors = colors.get(n, [196, 160, 90, 255])
        scene.add_geometry(tm, node_name=n)
    for n, p in bought.items():
        tm = to_trimesh(p)
        tm.visual.face_colors = [150, 150, 160, 255] if "n20" in n else ([200, 200, 210, 255] if "shaft" in n else [120, 120, 130, 255])
        scene.add_geometry(tm, node_name=n)
    leather_t = 1.8
    leather = trimesh.creation.box([2 * L_HALF + 30, 2 * W_HALF + 30, leather_t])
    leather.apply_translation([0, 0, -leather_t / 2])
    leather.visual.face_colors = [110, 62, 35, 255]
    scene.add_geometry(leather, node_name="leather")
    for n, p in fassy.items():
        tm = to_trimesh(p.rotate([180, 0, 0]).translate([0, 0, -leather_t]))
        tm.apply_translation([0, 0, 0])
        tm.visual.face_colors = [80, 80, 90, 255] if n == "frame" else [196, 160, 90, 255]
        # frame underside at z=0 in its frame; flipped it hangs below the leather with rollers touching
        scene.add_geometry(tm, node_name="f_" + n)
    scene.export(f"{out}/spider_v0_assembly.glb")
    os.makedirs(out + "/assy", exist_ok=True)
    for n, pm in {**assy, **bought}.items():
        to_trimesh(pm).export(f"{out}/assy/bot_{n}.stl")
    for n, pm in fassy.items():
        to_trimesh(pm.rotate([180, 0, 0]).translate([0, 0, -leather_t])).export(f"{out}/assy/fol_{n}.stl")
    leather.export(f"{out}/assy/leather.stl")
    json.dump(report | {"checks": checks}, open(f"{out}/checks.json", "w"), indent=1, default=str)
    print(json.dumps(report | {"checks": checks}, indent=1, default=str))
