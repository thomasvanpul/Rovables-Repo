#!/usr/bin/env python3
"""How much of each part does a sliced plate actually print? (added in this fork)

These parts were drawn for a resin printer; some walls are thinner than one
extrusion line. A slicer drops what it cannot fit and still returns success, so
a clean slice does not mean a whole part. This reads the G-code inside a sliced
.3mf and, for every part, compares the plastic laid down as model (walls, infill,
top and bottom; not supports or brim) with the volume of the part.

    python3 printables/slice_check.py printables/plates/rovables_all_P1S_0.4mm.3mf

A part is named by matching each sliced object's footprint and height to parts.json. The
figure is a ratio: 20% infill keeps it under 1 for a thick part, and a thin
part that prints whole lands near 1. A drop between two slices of the same
part is plastic the slicer left out.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import sys
import zipfile
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
FILAMENT_DIAMETER = 1.75                       # mm, Bambu PLA
NOT_MODEL = ("support", "brim", "skirt", "custom", "prime", "wipe")   # feature names that are not the part
MOVE = re.compile(r"^G[123]\s")
WORD = re.compile(r"([XYE])(-?\d*\.?\d+)")


def objects_in(gcode: str) -> dict[str, dict]:
    """Per labelled object: model filament length, and the XY box of its model moves."""
    out: dict[str, dict] = defaultdict(lambda: {"e": 0.0, "z": 0.0, "x": [math.inf, -math.inf], "y": [math.inf, -math.inf]})
    current, feature, x, y, z = None, "", 0.0, 0.0, 0.0
    for line in gcode.splitlines():
        if line.startswith("; start printing object"):
            current = line.rsplit(":", 1)[1].strip()
        elif line.startswith("; stop printing object"):
            current = None
        elif line.startswith("; Z_HEIGHT:"):
            z = float(line.split(":", 1)[1])
        elif line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip().lower()
        elif MOVE.match(line):
            words = dict(WORD.findall(line.split(";", 1)[0]))
            x, y = float(words.get("X", x)), float(words.get("Y", y))
            e = float(words.get("E", 0))
            if current and e > 0 and ("X" in words or "Y" in words) and not any(n in feature for n in NOT_MODEL):
                o = out[current]
                o["e"] += e
                o["z"] = max(o["z"], z)
                o["x"] = [min(o["x"][0], x), max(o["x"][1], x)]
                o["y"] = [min(o["y"][0], y), max(o["y"][1], y)]
    return out


def check(plate: pathlib.Path) -> dict:
    parts = json.loads((HERE / "parts.json").read_text())["parts"]
    with zipfile.ZipFile(plate) as z:
        gcode = z.read("Metadata/plate_1.gcode").decode("utf-8", "replace")
    setting = {k: v.strip() for k, v in re.findall(r"^; (wall_generator|detect_thin_wall|nozzle_diameter) = (.*)$", gcode, re.MULTILINE)}
    area = math.pi * (FILAMENT_DIAMETER / 2) ** 2
    by_part: dict[str, list[float]] = defaultdict(list)
    for o in objects_in(gcode).values():
        w, d = o["x"][1] - o["x"][0], o["y"][1] - o["y"][0]
        part = min(parts, key=lambda p, w=w, d=d, h=o["z"]: (p["size_mm"][0] - w) ** 2 + (p["size_mm"][1] - d) ** 2
                   + (p["size_mm"][2] - h) ** 2)
        by_part[part["part"]].append(o["e"] * area / part["volume_mm3"])
    rows = {name: {"copies": len(v), "printed_fraction_min": round(min(v), 3), "printed_fraction_max": round(max(v), 3)}
            for name, v in sorted(by_part.items())}
    return {"plate": plate.name, "settings": setting, "parts": rows}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        res = check(pathlib.Path(arg))
        print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
