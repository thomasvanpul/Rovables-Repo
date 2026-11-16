#!/usr/bin/env python3
"""Rovables printables: repair, orient, check and plate the mechanical parts for an FDM printer.

One source for everything under printables/: run it and stl/, plates/ and parts.json are rebuilt.

    python3 printables/build_printables.py            # repair + orient + check
    python3 printables/build_printables.py --slice    # also slice the plates with Bambu Studio

Inputs are the STLs under mechanical/converted/stl, which were exported from the authors'
SolidWorks 2016 parts (see mechanical/converted/README.md). Nothing here changes the geometry
of a part: it only fills pinholes in the mesh, rotates the part onto its best face and drops
it onto the bed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import zipfile

import numpy as np
import trimesh

# ---------------------------------------------------------------- parameters
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "mechanical" / "converted" / "stl"
OUT = ROOT / "printables"

ROBOT_SETS = 2                 # robots to print parts for (the boards are costed for 2 sets too)
OVERHANG_DEG = 45.0            # a face steeper than this from vertical, facing down, needs support
BED_EPS = 0.05                 # mm: a face this close to z=0 sits on the bed, not an overhang
HEIGHT_WEIGHT = 0.5            # mm2 of overhang one mm of extra height is worth when choosing a pose
BED_WEIGHT = 3.0               # mm2 of overhang one mm2 of flat bed contact is worth: small parts must sit on a face
PLA_DENSITY = 1.24             # g/cm3, for the solid-part mass in parts.json

BED = 256.0                    # mm, P1S and X1C
GRID_MARGIN = 30.0             # mm kept clear at the bed edge (purge line, brims)
GRID_GAP = 10.0                # mm between parts: room for brims and tree supports
PRINTER = "P1S"                # used in the plate file names
BAMBU_APP = "/Applications/BambuStudio.app"          # macOS; the script only needs its CLI and stock profiles
BED_TYPE = "Textured PEI Plate"
# Main plate: 0.4 mm nozzle, 0.12 mm layers, 3 walls, 20% gyroid.
STANDARD_NOZZLE = {"machine": "Bambu Lab P1S 0.4 nozzle", "process": "0.12mm Fine @BBL X1C",
                   "filament": "Bambu PLA Basic @BBL P1S 0.4 nozzle"}
# Second plate, robot parts only, for a 0.2 mm nozzle: the hub walls are 0.75 mm, under two 0.4 mm lines.
FINE_NOZZLE = {"machine": "Bambu Lab P1S 0.2 nozzle", "process": "0.10mm Standard @BBL X1C 0.2 nozzle",
               "filament": "Bambu PLA Basic @BBL X1C 0.2 nozzle"}
ROBOT_PARTS = ("base_plate_v1", "bottom_ski_v1", "case_minimum_covered", "BB_Mg_Adapter_V2", "Mt_Mg_Adapter_V2",
               "Magnet_Holder_V1C")
# These parts were drawn for a 25 micron resin printer and overhang everywhere, so supports are on.
PROCESS_OVERRIDES = {"wall_loops": 3, "sparse_infill_density": "20%", "sparse_infill_pattern": "gyroid",
                     "enable_support": 1, "support_type": "tree(auto)", "brim_type": "auto_brim",
                     # Arachne varies the line width to fit thin walls. The classic generator these
                     # profiles default to laid the 4 mm magnet rod at 147% of its volume on a 0.4 mm
                     # nozzle with no warning (slice_check.py, printables/README.md).
                     "wall_generator": "arachne"}

# part -> (what it is, copies per robot set, copies regardless of sets, printed in PLA?)
PARTS = {
    "base_plate_v1": ("Main body (chassis): carries both motors, bearings, encoder boards and standoffs", 1, 0, True),
    "bottom_ski_v1": ("Undercarriage: clamps the two motors into the main body from below", 1, 0, True),
    "case_minimum_covered": ("Cover over the electronics and battery", 1, 0, True),
    "BB_Mg_Adapter_V2": ("Ball bearing adapter: idler-side wheel hub, holds the ring magnets", 2, 0, True),
    "Mt_Mg_Adapter_V2": ("Motor adapter: driven-side wheel hub on the motor shaft, holds the ring magnets", 2, 0, True),
    "Magnet_Holder_V1C": ("Rod for magnets: goes behind the fabric with a ring magnet on each end", 1, 0, True),
    "Chassis_encoder_inside_v2": ("Earlier chassis with the encoders inside (assemblies v1 to v3); one copy for comparison", 0, 1, True),
    "top_part_joystick_v1": ("Joystick controller enclosure, top", 0, 1, True),
    "bottom_part_joystick_v1": ("Joystick controller enclosure, bottom", 0, 1, True),
    "rubber_wheels_v1": ("Tyre. The paper used 1 mm neoprene; print in TPU or cut from sheet, not PLA", 0, 0, False),
    "radio_dungle": ("Model of the bought USB radio dongle, for fit only; not a printed part", 0, 0, False),
}
# Poses the scorer gets wrong, as (axis, degrees) applied to the converted STL before dropping to the bed.
ORIENT_OVERRIDE: dict[str, tuple[tuple[float, float, float], float]] = {
    # wheel hubs: axis vertical so the wheel prints round; the scorer stood them on their rim
    # bearing pin on the bed, cup opening up. Cup-down fails on a 0.4 mm nozzle: the rim is 0.33 mm wide,
    # narrower than one line, so the first layer is empty and the slicer moves the part to a second plate.
    "BB_Mg_Adapter_V2": ((1, 0, 0), -90.0),
    "Mt_Mg_Adapter_V2": ((1, 0, 0), 90.0),      # shaft hub on the bed, wheel disc above it on supports
    # chassis: lying flat (11 and 15 mm tall) on supports, not standing 25 mm tall on 5 mm2 of contact
    "base_plate_v1": ((1, 0, 0), -90.0),
    "Chassis_encoder_inside_v2": ((1, 0, 0), 90.0),
}
# ---------------------------------------------------------------------------


def repair(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, int]:
    """Fill pinholes left by tessellation. Returns the mesh and how many faces were added."""
    before = len(mesh.faces)
    if not mesh.is_watertight:
        mesh.fill_holes()
        mesh.fix_normals()
    return mesh, len(mesh.faces) - before


def overhang_area(mesh: trimesh.Trimesh) -> float:
    limit = -np.cos(np.radians(OVERHANG_DEG))
    down = mesh.face_normals[:, 2] < limit
    off_bed = mesh.triangles_center[:, 2] > BED_EPS
    return float(mesh.area_faces[down & off_bed].sum())


def bed_area(mesh: trimesh.Trimesh) -> float:
    on = (mesh.triangles_center[:, 2] <= BED_EPS) & (mesh.face_normals[:, 2] < -0.99)
    return float(mesh.area_faces[on].sum())


def drop(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    lo, hi = mesh.bounds
    mesh.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return mesh


def orient(name: str, mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict]:
    """Pick the resting pose with the least unsupported area, then the most bed contact."""
    if name in ORIENT_OVERRIDE:
        axis, deg = ORIENT_OVERRIDE[name]
        m = mesh.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), axis))
        m = drop(m)
        return m, {"pose": "override", "overhang_mm2": round(overhang_area(m), 1), "bed_mm2": round(bed_area(m), 1)}
    # The parts were drawn square to the axes, so the six axis-up poses come first, then the resting poses.
    rot = trimesh.transformations.rotation_matrix
    poses = [("+z", np.eye(4)), ("-z", rot(np.pi, [1, 0, 0])), ("+y", rot(np.pi / 2, [1, 0, 0])),
             ("-y", rot(-np.pi / 2, [1, 0, 0])), ("+x", rot(-np.pi / 2, [0, 1, 0])), ("-x", rot(np.pi / 2, [0, 1, 0]))]
    stable, _ = trimesh.poses.compute_stable_poses(mesh, n_samples=1, threshold=0.0)
    poses += [(f"rest{i}", t) for i, t in enumerate(stable)]
    best = None
    for label, t in poses:
        m = mesh.copy()
        m.apply_transform(t)
        m = drop(m)
        oh, bed = overhang_area(m), bed_area(m)
        score = oh - BED_WEIGHT * bed + HEIGHT_WEIGHT * float(m.extents[2])
        if best is None or score < best[0]:
            best = (score, m, {"pose": label, "poses_tried": len(poses), "overhang_mm2": round(oh, 1), "bed_mm2": round(bed, 1)})
    return best[1], best[2]


def build() -> list[dict]:
    stl_dir = OUT / "stl"
    shutil.rmtree(stl_dir, ignore_errors=True)
    stl_dir.mkdir(parents=True)
    rows = []
    for name, (what, per_set, fixed, pla) in PARTS.items():
        mesh = trimesh.load(SRC / f"{name}.stl", force="mesh")
        mesh, filled = repair(mesh)
        mesh, pose = orient(name, mesh)
        path = stl_dir / f"{name}.stl"
        mesh.export(path)
        check = trimesh.load(path, force="mesh")
        qty = per_set * ROBOT_SETS + fixed
        rows.append({"part": name, "what": what, "qty": qty, "pla": pla, "stl": str(path.relative_to(ROOT)),
                     "watertight": bool(check.is_watertight), "winding": bool(check.is_winding_consistent),
                     "faces_filled": filled, "size_mm": [round(float(x), 2) for x in check.extents],
                     "volume_mm3": round(float(check.volume), 1),
                     "solid_grams": round(float(check.volume) / 1000 * PLA_DENSITY, 2), **pose})
    return rows


def flatten(kind: str, name: str) -> dict:
    """A stock Bambu Studio profile with everything it inherits folded in."""
    profiles = pathlib.Path(BAMBU_APP) / "Contents" / "Resources" / "profiles" / "BBL"
    hits = list(profiles.rglob(f"{name}.json"))
    if not hits:
        raise FileNotFoundError(f"Bambu Studio profile not found: {name}")
    d = json.loads(hits[0].read_text())
    parent = d.pop("inherits", None)
    if parent:
        d = {**flatten(kind, parent), **d}
    return d


def preset(kind: str, name: str, over: dict | None, out: pathlib.Path) -> str:
    d = flatten(kind, name)
    d.update({"name": name, "from": "system", "type": kind})
    for k, v in (over or {}).items():
        d[k] = str(v)          # the profiles hold every value as a string; an int is silently ignored
    path = out / f"{kind}_{name}.json".replace(" ", "_").replace("@", "")
    path.write_text(json.dumps(d, indent=1))
    return str(path)


def slice_plate(tag: str, rows: list[dict], nozzle: dict) -> dict:
    wd = OUT / "plates" / "_work" / tag
    shutil.rmtree(wd, ignore_errors=True)
    st = wd / "_settings"
    st.mkdir(parents=True)
    m = preset("machine", nozzle["machine"], None, st)
    p = preset("process", nozzle["process"], dict(PROCESS_OVERRIDES, curr_bed_type=BED_TYPE), st)
    f = preset("filament", nozzle["filament"], None, st)
    # Laid out here in rows, biggest first, with the slicer's own arrange off: on the 0.4 mm plate its
    # arranger sent the four bearing hubs to a second plate in every pose tried, with most of the bed empty.
    stls = []
    x = y = GRID_MARGIN
    row_depth = 0.0
    todo = [r for r in sorted(rows, key=lambda r: -r["size_mm"][0] * r["size_mm"][1]) for _ in range(r["qty"])]
    for i, r in enumerate(todo):
        w, d = r["size_mm"][0], r["size_mm"][1]
        if x + w > BED - GRID_MARGIN:
            x, y, row_depth = GRID_MARGIN, y + row_depth + GRID_GAP, 0.0
        if y + d > BED - GRID_MARGIN:
            raise SystemExit(f"{tag}: {r['part']} does not fit the bed; split the plate")
        mesh = trimesh.load(ROOT / r["stl"], force="mesh")
        mesh.apply_translation([x + w / 2, y + d / 2, 0])
        placed = wd / f"{i:02d}_{r['part']}.stl"
        mesh.export(placed)
        stls.append(str(placed))
        x, row_depth = x + w + GRID_GAP, max(row_depth, d)
    cmd = [BAMBU_APP + "/Contents/MacOS/BambuStudio", "--load-settings", f"{m};{p}", "--load-filaments", f, "--arrange", "0", "--orient", "0",
           "--slice", "0", "--outputdir", str(wd), "--export-3mf", f"{tag}.3mf"] + stls
    run = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=1500, check=False)
    res = json.loads((wd / "result.json").read_text()) if (wd / "result.json").exists() else {}
    plates = res.get("sliced_plates", [])
    out3mf = OUT / "plates" / f"{tag}.3mf"
    info = {}
    if (wd / f"{tag}.3mf").exists():
        shutil.copy(wd / f"{tag}.3mf", out3mf)
        with zipfile.ZipFile(out3mf) as z:
            cfg = json.loads(z.read("Metadata/project_settings.config"))
            info = {"process": cfg.get("print_settings_id"), "layer": cfg.get("layer_height"),
                    "walls": cfg.get("wall_loops"), "infill": cfg.get("sparse_infill_density"),
                    "support": cfg.get("enable_support"), "nozzle": cfg.get("nozzle_diameter")}
            for n in z.namelist():
                if n.endswith("plate_1.png"):
                    (OUT / "plates" / f"{tag}.png").write_bytes(z.read(n))
    return {"tag": tag, "rc": run.returncode, "slicer_rc": res.get("return_code"), "error": res.get("error_string"),
            "stderr": run.stderr[-300:], "objects": len(stls), "slicer_plates": len(plates),
            "seconds": int(sum(q.get("total_predication", 0) for q in plates)),
            "grams": round(sum(fl["total_used_g"] for q in plates for fl in q.get("filaments", [])), 2),
            "warnings": [q.get("warning_message", "") for q in plates if q.get("warning_message")],
            "printer": PRINTER, "process": info.get("process"), "layer": info.get("layer"), "walls": info.get("walls"),
            "infill": info.get("infill"), "support": info.get("support"), "nozzle": info.get("nozzle"), "file": str(out3mf.relative_to(ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", action="store_true", help="slice the plates with Bambu Studio")
    a = ap.parse_args()
    rows = build()
    result = {"robot_sets": ROBOT_SETS, "parts": rows, "plates": []}
    bad = [r["part"] for r in rows if not r["watertight"]]
    for r in rows:
        print(f"{r['part']:28s} x{r['qty']} watertight={r['watertight']} size={r['size_mm']} "
              f"overhang={r['overhang_mm2']} bed={r['bed_mm2']} filled={r['faces_filled']}")
    if a.slice:
        (OUT / "plates").mkdir(exist_ok=True)
        todo = [r for r in rows if r["pla"] and r["qty"]]
        jobs = [(f"rovables_all_{PRINTER}_0.4mm", todo, STANDARD_NOZZLE),
                (f"rovables_robot_{PRINTER}_0.2mm", [r for r in todo if r["part"] in ROBOT_PARTS], FINE_NOZZLE)]
        for tag, part_rows, nozzle in jobs:
            s = slice_plate(tag, part_rows, nozzle)
            result["plates"].append(s)
            print(json.dumps(s, indent=1))
            if s["rc"] != 0 or s["slicer_plates"] != 1:
                bad.append(s["tag"])
        shutil.rmtree(OUT / "plates" / "_work", ignore_errors=True)
    else:
        old = OUT / "parts.json"
        if old.exists():
            result["plates"] = json.loads(old.read_text()).get("plates", [])
    (OUT / "parts.json").write_text(json.dumps(result, indent=1))
    if bad:
        print("FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
