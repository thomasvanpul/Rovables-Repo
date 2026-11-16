#!/usr/bin/env python3
"""Build the Rovable v2 printed parts from rovable_v2_geom.py and check them.

    python v2/cad/build.py            # STLs in print orientation, checks, parts.json
    python v2/cad/build.py --slice    # also slice one P1S plate with Bambu Studio

Needs manifold3d, trimesh and numpy. Exit code is non-zero if any check fails.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from manifold3d import Manifold

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import rovable_v2_geom as g

OUT = HERE / "export"
SEGMENTS = 96
PLA_DENSITY = 1.24            # g/cm3
BED = 256.0                   # mm, P1S and X1C
TOUCH = 0.01                  # mm3: shared volume below this is two faces touching, not a clash
PROCESS = "0.20mm Standard @BBL X1C"
PLATE_TAG = "rovable_v2_P1S_0.4mm"


def _cyl(h, r):
    return Manifold.cylinder(h, r, r, SEGMENTS)


class K:
    """manifold3d kernel with the interface rovable_v2_geom expects."""
    box = staticmethod(lambda x0, x1, y0, y1, z0, z1: Manifold.cube([abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)])
                       .translate([min(x0, x1), min(y0, y1), min(z0, z1)]))
    cylx = staticmethod(lambda x0, x1, y, z, r: _cyl(abs(x1 - x0), r).rotate([0, 90, 0]).translate([min(x0, x1), y, z]))
    cylz = staticmethod(lambda x, y, z0, z1, r: _cyl(abs(z1 - z0), r).translate([x, y, min(z0, z1)]))
    U = staticmethod(lambda a, b: a + b)
    D = staticmethod(lambda a, b: a - b)


# name -> (solid in the assembly frame, rotation that puts it in print orientation, copies per robot, spares, note)
def printed():
    return {
        "chassis": (g.chassis(K), [180, 0, 0], 1, 0, "deck on the bed, tunnels bridge"),
        "tray": (g.tray(K), [0, 0, 0], 1, 0, "floor on the bed"),
        "roller_body": (g.roller_body(K), [0, 90, 0], 2, 2, "hub end down, open bore up"),
        "roller_cap": (g.roller_cap(K), [0, -90, 0], 2, 2, "flange down, plug up"),
        "motor_cap": (g.motor_cap(K), [0, 90, 0], 2, 0, "flange down"),
    }


def to_mesh(m: Manifold) -> trimesh.Trimesh:
    mg = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mg.vert_properties)[:, :3], np.asarray(mg.tri_verts), process=True)


def assembly():
    """Every solid in its assembled place: both units, the tray and the bought parts."""
    parts = {"chassis": g.chassis(K), "tray": g.tray(K)}
    for s, t in ((1, "front"), (-1, "back")):
        parts[f"roller_body {t}"] = g.roller_body(K, s)
        parts[f"roller_cap {t}"] = g.roller_cap(K, s)
        parts[f"motor_cap {t}"] = g.motor_cap(K, s)
    return parts, g.refs(K)


# pairs that are meant to share volume: press fits and a screw cutting its own thread
INTENDED = (("roller_cap", "M3 axle screw"), ("roller_body", "roller_cap"))


def clashes():
    parts, refs = assembly()
    solids = {**parts, **refs}
    names = sorted(solids)
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a in refs and b in refs and "Fabric" not in a + b:
                continue
            v = (solids[a] ^ solids[b]).volume()
            if v <= TOUCH:
                continue
            same_unit = ("front" in a) == ("front" in b) and ("back" in a) == ("back" in b)
            if same_unit and any(p in a + b and q in a + b for p, q in INTENDED):
                continue
            found.append((a, b, round(v, 2)))
    return found


def checks(rows):
    c = []
    c.append(("all parts watertight", all(r["watertight"] for r in rows)))
    c.append(("all parts one solid", all(r["bodies"] == 1 for r in rows)))
    c.append(("all parts fit the bed", all(max(r["size_mm"][:2]) < BED - 60 for r in rows)))
    bad = clashes()
    c.append((f"no clash between any two parts in the assembly ({len(bad)} found: {bad[:4]})", not bad))
    c.append(("magnet fits the bore with 0.1 to 0.2 radial clearance", 0.1 <= g.BORE_R - g.MAG_D / 2 <= 0.2))
    c.append(("magnet and cap plug fit the bore length", g.MAG_L + g.PLUG_L <= g.BORE_L + 1e-6))
    c.append(("shaft tip stays inside the D hole", g.N20_SHAFT_L < g.U_ROLLER0 + g.HUB_L))
    c.append(("roller clears the deck", g.DECK_Z - g.DECK_T - 2 * g.AX >= 0.5))
    c.append(("roller is the lowest point (chassis clear of the fabric)", g.FLOOR_Z > 0))
    wall = g.YA - (g.AX + g.WELL_CLEAR) - g.TRAY_SCREW_Y - g.TRAY_PILOT_R
    c.append((f"tray screw pilot keeps a wall to the roller well ({wall:.2f} mm)", wall >= 1.0))
    lay = g.tray_layout()
    inside = all(-g.HALF_X + g.RIM_T <= v[0] and v[1] <= g.HALF_X - g.RIM_T and -g.HALF_Y + g.RIM_T <= v[2]
                 and v[3] <= g.HALF_Y - g.RIM_T for v in lay.values())
    c.append(("every board pocket is inside the tray rim", inside))
    row_y1 = max(lay[n][3] for n in ("mcu", "driver", "imu"))
    c.append(("battery pocket clears the board row", lay["battery"][2] - g.RIB_T > row_y1 + g.RIB_T))
    return c


def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "stl").mkdir(exist_ok=True)
    rows = []
    for name, (solid, rot, per_robot, spares, note) in printed().items():
        mesh = to_mesh(solid.rotate(rot))
        lo, hi = mesh.bounds                      # centred in X and Y, sitting on Z = 0, as printables/ does
        mesh.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        path = OUT / "stl" / f"{name}.stl"
        mesh.export(path)
        rows.append({"part": name, "stl": str(path.relative_to(ROOT)), "qty": per_robot + spares, "per_robot": per_robot,
                     "spares": spares, "print": note, "watertight": bool(mesh.is_watertight),
                     "bodies": int(mesh.body_count), "size_mm": [round(float(v), 2) for v in mesh.extents],
                     "volume_mm3": round(float(mesh.volume), 1),
                     "solid_grams": round(float(mesh.volume) * PLA_DENSITY / 1000, 2)})
    return rows


def slice_plate(rows):
    """Reuse the fork's plate slicer (printables/build_printables.py) with this folder as its output."""
    sys.path.insert(0, str(ROOT / "printables"))
    import build_printables as bp
    bp.OUT = OUT
    (OUT / "plates").mkdir(exist_ok=True)
    # These parts were drawn for FDM: no supports, and Arachne for the 1.4 mm roller wall.
    bp.PROCESS_OVERRIDES = {"wall_loops": 3, "sparse_infill_density": "20%", "sparse_infill_pattern": "gyroid",
                            "enable_support": 0, "brim_type": "auto_brim", "wall_generator": "arachne"}
    res = bp.slice_plate(PLATE_TAG, rows, dict(bp.STANDARD_NOZZLE, process=PROCESS))
    res["file"] = str((OUT / "plates" / f"{PLATE_TAG}.3mf").relative_to(ROOT))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slice", action="store_true", help="slice the plate with Bambu Studio")
    args = ap.parse_args()
    rows = build()
    result = {"parts": rows, "checks": [{"check": n, "ok": bool(ok)} for n, ok in checks(rows)],
              "robot_printed_grams_solid": round(sum(r["solid_grams"] * r["per_robot"] for r in rows), 1),
              "envelope_mm": [round(2 * g.HALF_X + 3.2, 1), round(2 * g.HALF_Y, 1), round(g.TRAY_Z1 + g.RIM_H, 1)],
              "track_mm": round(2 * abs(g.ux(1, g.U_BORE0 + g.MAG_L / 2)), 1), "axis_pitch_mm": g.AXIS_PITCH}
    old = OUT / "parts.json"
    if args.slice:
        result["plate"] = slice_plate(rows)
    elif old.exists():
        prev = json.loads(old.read_text()).get("plate")
        if prev:
            result["plate"] = dict(prev, stale="STLs rebuilt since this slice; run --slice again")
    old.write_text(json.dumps(result, indent=1))
    for r in rows:
        print(f"{r['part']:12s} watertight={r['watertight']} bodies={r['bodies']} size={r['size_mm']} x{r['qty']}")
    failed = [c for c in result["checks"] if not c["ok"]]
    for c in result["checks"]:
        print("PASS" if c["ok"] else "FAIL", c["check"])
    if "plate" in result and args.slice:
        p = result["plate"]
        print(f"plate rc={p['rc']} slicer_rc={p['slicer_rc']} objects={p['objects']} plates={p['slicer_plates']} "
              f"{p['seconds'] // 60} min {p['grams']} g warnings={p['warnings']}")
        if p["rc"] != 0 or p["slicer_rc"] not in (0, None) or p["slicer_plates"] != 1:
            failed.append({"check": "plate slices"})
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
