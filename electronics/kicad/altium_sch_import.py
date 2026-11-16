#!/usr/bin/env python3
"""Altium .SchDoc -> KiCad .kicad_sch, headless (added in this fork).

KiCad 10.0.3 can only import an Altium schematic from the schematic editor's
window; kicad-cli has no schematic import. This reads the .SchDoc directly
(an OLE compound file holding pipe-delimited records) and writes a KiCad
schematic: each placed component becomes its own library symbol drawn from the
Altium graphics, with wires, junctions, net labels and power ports carried over.

    python3 electronics/kicad/altium_sch_import.py            # all four boards
    python3 electronics/kicad/altium_sch_import.py --check    # also netlist, ERC, PDF, compare with the board

The check exports a netlist from the new schematic with kicad-cli and compares
it, pin by pin, with the nets on the imported board (sch_check.json per board).
Standard library only; the check needs KiCad for kicad-cli and its Python.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import re
import struct
import subprocess
import uuid
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ELEC = HERE.parent
KICAD = pathlib.Path("/Applications/KiCad/KiCad.app/Contents")
KICAD_CLI = KICAD / "MacOS/kicad-cli"
KICAD_PY = KICAD / "Frameworks/Python.framework/Versions/Current/bin/python3"

# board folder -> Altium schematic, relative to electronics/
BOARDS = {
    "motor_driver_v3": "Motor driver v3/schematic_motor_driver_v3.SchDoc",
    "ir_encoder_v2": "IR encoder/Schematic_IR_encoder_v2.SchDoc",
    "programming_shield": "Programming adapter/Schematic_shield_Rovables_v2.SchDoc",
    "master_board": "master board/schematic_rovables_master_v1.SchDoc",
}

UNIT_MM = 0.254            # one Altium schematic unit is 10 mil
FRAC = 100000              # *_FRAC fields are 1/100000 of a unit
MARGIN_UNITS = 60          # space left around the drawing on the KiCad sheet
PAPERS = [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594)]
TEXT_MM = 1.27
STROKE_MM = 0.1524
PIN_TYPES = {0: "input", 1: "bidirectional", 2: "output", 3: "open_collector",
             4: "passive", 5: "tri_state", 6: "open_emitter", 7: "power_in"}
FREE_SECT = 0xFFFFFFFA     # compound-file sector ids at or above this are markers
END_OF_TREE = 0xFFFFFFFF


# ---------------------------------------------------------------- reading

def read_streams(path: pathlib.Path) -> dict[str, bytes]:
    """Every stream in an OLE compound file, keyed by path."""
    d = path.read_bytes()
    if d[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError(f"{path} is not an OLE compound file")
    ssz = 1 << struct.unpack_from("<H", d, 30)[0]
    msz = 1 << struct.unpack_from("<H", d, 32)[0]
    _nfat, dir_start, _, cutoff, minifat_start, _n, difat_start, _nd = struct.unpack_from("<8I", d, 44)

    def sector(n: int) -> bytes:
        return d[(n + 1) * ssz:(n + 2) * ssz]

    difat = list(struct.unpack_from("<109I", d, 76))
    nxt = difat_start
    while nxt < FREE_SECT:
        block = struct.unpack(f"<{ssz // 4}I", sector(nxt))
        difat += block[:-1]
        nxt = block[-1]
    fat: list[int] = []
    for s in difat:
        if s < FREE_SECT:
            fat += struct.unpack(f"<{ssz // 4}I", sector(s))

    def chain(start: int, table=fat, get=sector) -> bytes:
        out, s, seen = [], start, 0
        while s < FREE_SECT:
            out.append(get(s))
            s = table[s]
            seen += 1
            if seen > len(table):
                raise ValueError(f"{path}: sector chain loops")
        return b"".join(out)

    dir_bytes = chain(dir_start)
    entries = []
    for i in range(0, len(dir_bytes), 128):
        e = dir_bytes[i:i + 128]
        name_len = struct.unpack_from("<H", e, 64)[0]
        if not name_len:
            entries.append(None)
            continue
        left, right, child = struct.unpack_from("<3I", e, 68)
        entries.append((e[:name_len - 2].decode("utf-16le"), e[66], left, right, child,
                        struct.unpack_from("<I", e, 116)[0],
                        struct.unpack_from("<Q", e, 120)[0] & 0xFFFFFFFF))
    root = entries[0]
    mini = chain(root[5])[:root[6]]
    mini_fat_raw = chain(minifat_start) if minifat_start < FREE_SECT else b""
    mini_fat = struct.unpack(f"<{len(mini_fat_raw) // 4}I", mini_fat_raw)
    streams: dict[str, bytes] = {}

    def walk(i: int, prefix: str) -> None:
        if i == END_OF_TREE or entries[i] is None:
            return
        name, kind, left, right, child, start, size = entries[i]
        walk(left, prefix)
        walk(right, prefix)
        if kind == 2:
            if size >= cutoff:
                streams[prefix + name] = chain(start)[:size]
            else:
                streams[prefix + name] = chain(start, mini_fat, lambda n: mini[n * msz:(n + 1) * msz])[:size]
        elif kind == 1:
            walk(child, prefix + name + "/")

    walk(root[4], "")
    return streams


def read_records(path: pathlib.Path) -> list[dict[str, str]]:
    """The schematic's records, without the file header record. An object's
    OWNERINDEX is its owner's position in this list."""
    data = read_streams(path)["FileHeader"]
    out, i = [], 0
    while i + 4 <= len(data):
        n = struct.unpack_from("<I", data, i)[0] & 0xFFFFFF
        raw = data[i + 4:i + 4 + n]
        i += 4 + n
        rec = {}
        for pair in raw.rstrip(b"\0").decode("latin-1").split("|"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                rec[k.upper()] = v
        out.append(rec)
    return out[1:]


def coord(rec: dict, key: str) -> int:
    """A coordinate in 1/100000 of an Altium unit, as an exact integer."""
    return int(rec.get(key, 0)) * FRAC + int(rec.get(key + "_FRAC", 0))


def point(rec: dict, key: str = "LOCATION") -> tuple[int, int]:
    return coord(rec, key + ".X"), coord(rec, key + ".Y")


def points(rec: dict) -> list[tuple[int, int]]:
    return [(coord(rec, f"X{i}"), coord(rec, f"Y{i}")) for i in range(1, int(rec.get("LOCATIONCOUNT", 0)) + 1)]


# ---------------------------------------------------------------- writing

def uid() -> str:
    return str(uuid.uuid4())


def q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def mm(v: int) -> str:
    s = f"{v * UNIT_MM / FRAC:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_+.-]", "_", name) or "X"


FONT = f"(effects (font (size {TEXT_MM} {TEXT_MM})) (justify left bottom))"
HIDDEN = f"(effects (font (size {TEXT_MM} {TEXT_MM})) (hide yes))"
STROKE = f"(stroke (width {STROKE_MM}) (type default))"


class Sheet:
    """Turns one Altium sheet into KiCad text. Altium's Y grows upward and
    KiCad's sheet Y grows downward; library symbols keep Y up."""

    def __init__(self, records: list[dict[str, str]], name: str):
        self.recs = records
        self.name = name
        self.root = uid()
        self.comps = {i: r for i, r in enumerate(records) if r.get("RECORD") == "1"}
        self._segments = [seg for r in records if r.get("RECORD") == "27" for seg in itertools.pairwise(points(r))]
        self._marks = {point(r) for r in records if r.get("RECORD") in ("17", "25")}
        xs, ys = [], []
        for r in records:
            if r.get("RECORD") in ("1", "2", "4", "6", "13", "17", "25", "27", "29"):
                for x, y in ([point(r)] if "LOCATION.X" in r else []) + points(r):
                    xs.append(x)
                    ys.append(y)
        self.x0 = min(xs) - MARGIN_UNITS * FRAC
        top = max(ys) + MARGIN_UNITS * FRAC
        # keep the 100 mil grid: shift by whole 10-unit steps only
        step = 10 * FRAC
        self.x0 = (self.x0 // step) * step
        self.top = -(-top // step) * step
        w = (max(xs) - self.x0) * UNIT_MM / FRAC + MARGIN_UNITS * UNIT_MM
        h = (self.top - min(ys)) * UNIT_MM / FRAC + MARGIN_UNITS * UNIT_MM
        self.paper = next((p for p, pw, ph in PAPERS if w <= pw and h <= ph), PAPERS[-1][0])

    # sheet coordinates
    def sx(self, x: int) -> str:
        return mm(x - self.x0)

    def sy(self, y: int) -> str:
        return mm(self.top - y)

    def at(self, p: tuple[int, int]) -> str:
        return f"{self.sx(p[0])} {self.sy(p[1])}"

    def children(self, owner: int, kinds: tuple[str, ...]) -> list[dict]:
        return [r for r in self.recs if r.get("RECORD") in kinds and r.get("OWNERINDEX") == str(owner)]

    def owned_by_component(self, rec: dict) -> bool:
        return "OWNERINDEX" in rec and int(rec["OWNERINDEX"]) in self.comps

    # ---- component data

    def designator(self, ci: int) -> str:
        d = self.children(ci, ("34",))
        return d[0].get("TEXT", "?") if d else "?"

    def parameter(self, ci: int, name: str) -> dict | None:
        for p in self.children(ci, ("41",)):
            if p.get("NAME", "").lower() == name.lower():
                return p
        return None

    def value(self, ci: int) -> str:
        p = self.parameter(ci, "Comment")
        text = p.get("TEXT", "") if p else ""
        if text.startswith("="):                     # "=Value" points at another parameter
            ref = self.parameter(ci, text[1:])
            text = ref.get("TEXT", "") if ref else text
        return text or self.comps[ci].get("LIBREFERENCE", "")

    def footprint(self, ci: int) -> str:
        """The current PCB model. Models hang off an implementation list that
        follows the component, so take them up to the next component."""
        nxt = min((i for i in self.comps if i > ci), default=len(self.recs))
        models = [r for r in self.recs[ci:nxt] if r.get("RECORD") == "45" and r.get("MODELTYPE") == "PCBLIB"]
        current = [m for m in models if m.get("ISCURRENT") == "T"] or models
        return current[0].get("MODELNAME", "") if current else ""

    def shown(self, ci: int, rec: dict) -> bool:
        part = rec.get("OWNERPARTID", "-1")
        return part in ("-1", "0", self.comps[ci].get("CURRENTPARTID", "1"))

    def pin_end(self, pin: dict) -> tuple[int, int]:
        """Where a wire attaches: the pin's far end from the body."""
        x, y = point(pin)
        length = coord(pin, "PINLENGTH")
        dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][int(pin.get("PINCONGLOMERATE", 0)) & 3]
        return x + dx * length, y + dy * length

    def touches_wiring(self, p: tuple[int, int]) -> bool:
        """Is this point on a wire, a power port or a net label?"""
        if p in self._marks:
            return True
        for a, b in self._segments:
            cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            if (cross == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                    and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])):
                return True
        return False

    # ---- library symbols

    def graphics(self, items: list[dict], origin: tuple[int, int]) -> list[str]:
        ox, oy = origin

        def rel(p):
            return f"(xy {mm(p[0] - ox)} {mm(p[1] - oy)})"

        out = []
        for r in items:
            kind = r["RECORD"]
            solid = "(fill (type outline))" if r.get("ISSOLID") == "T" else "(fill (type none))"
            if kind in ("6", "7"):
                pts = points(r)
                if kind == "7" and pts:
                    pts = pts + pts[:1]
                if len(pts) >= 2:
                    out.append(f"(polyline (pts {' '.join(rel(p) for p in pts)}) {STROKE} "
                               f"{solid if kind == '7' else '(fill (type none))'})")
            elif kind == "13":
                out.append(f"(polyline (pts {rel(point(r))} {rel(point(r, 'CORNER'))}) {STROKE} (fill (type none)))")
            elif kind == "14":
                a, b = point(r), point(r, "CORNER")
                fill = "(fill (type background))" if r.get("ISSOLID") == "T" else "(fill (type none))"
                out.append(f"(rectangle (start {mm(a[0] - ox)} {mm(a[1] - oy)}) "
                           f"(end {mm(b[0] - ox)} {mm(b[1] - oy)}) {STROKE} {fill})")
            elif kind == "12":
                cx, cy = point(r)
                rad = coord(r, "RADIUS")
                a0, a1 = float(r.get("STARTANGLE", 0)), float(r.get("ENDANGLE", 360))
                if abs((a1 - a0) % 360) < 1e-6:
                    out.append(f"(circle (center {mm(cx - ox)} {mm(cy - oy)}) (radius {mm(rad)}) {STROKE} (fill (type none)))")
                    continue
                if a1 < a0:
                    a1 += 360
                trio = []
                for a in (a0, (a0 + a1) / 2, a1):
                    trio.append((round(cx + rad * math.cos(math.radians(a))), round(cy + rad * math.sin(math.radians(a)))))
                out.append(f"(arc (start {mm(trio[0][0] - ox)} {mm(trio[0][1] - oy)}) "
                           f"(mid {mm(trio[1][0] - ox)} {mm(trio[1][1] - oy)}) "
                           f"(end {mm(trio[2][0] - ox)} {mm(trio[2][1] - oy)}) {STROKE} (fill (type none)))")
            elif kind == "4" and r.get("TEXT"):
                p = point(r)
                rot = (int(r.get("ORIENTATION", 0)) % 4) * 90
                out.append(f"(text {q(r['TEXT'])} (at {mm(p[0] - ox)} {mm(p[1] - oy)} {rot}) {FONT})")
        return out

    def pins(self, items: list[dict], origin: tuple[int, int]) -> list[str]:
        out = []
        for p in items:
            ex, ey = self.pin_end(p)
            cong = int(p.get("PINCONGLOMERATE", 0))
            angle = ((cong & 3) * 90 + 180) % 360
            etype = PIN_TYPES.get(int(p.get("ELECTRICAL", 4)), "passive")
            name = p.get("NAME", "") or "~"
            name_fx = f"(effects (font (size {TEXT_MM} {TEXT_MM}))" + ("" if cong & 0x08 else " (hide yes)") + ")"
            num_fx = f"(effects (font (size {TEXT_MM} {TEXT_MM}))" + ("" if cong & 0x10 else " (hide yes)") + ")"
            out.append(f"(pin {etype} line (at {mm(ex - origin[0])} {mm(ey - origin[1])} {angle}) "
                       f"(length {mm(coord(p, 'PINLENGTH'))}) (name {q(name)} {name_fx}) "
                       f"(number {q(p.get('DESIGNATOR', ''))} {num_fx}))")
        return out

    def build(self) -> str:
        libs, items = [], []
        by_ref: dict[str, list[int]] = defaultdict(list)
        for ci in self.comps:
            by_ref[self.designator(ci)].append(ci)

        # one library symbol per designator; a multi-part component gets one unit per placed part
        for n, (ref, cis) in enumerate(sorted(by_ref.items())):
            sym = safe(ref) if ref != "?" else f"unnamed{n}"
            prefix = re.match(r"[A-Za-z#]*", ref).group(0) or "U"
            first = cis[0]
            units = []
            # A pin drawn on more than one part (an op-amp's supply pins) is one
            # physical pin: keep it on the part where it is wired, once.
            shown = {ci: [r for r in self.children(ci, ("2",)) if self.shown(ci, r)] for ci in cis}
            keep: dict[str, tuple[int, bool]] = {}
            for ci in cis:
                for r in shown[ci]:
                    num = r.get("DESIGNATOR", "")
                    if num not in keep or (self.touches_wiring(self.pin_end(r)) and not keep[num][1]):
                        keep[num] = (ci, self.touches_wiring(self.pin_end(r)))
            for ci in cis:
                comp = self.comps[ci]
                origin = point(comp)
                unit = int(comp.get("CURRENTPARTID", 1)) if len(cis) > 1 else 1
                body = self.graphics([r for r in self.children(ci, ("4", "6", "7", "12", "13", "14")) if self.shown(ci, r)], origin)
                pins = self.pins([r for r in shown[ci] if keep[r.get("DESIGNATOR", "")][0] == ci], origin)
                units.append(f'  (symbol "{sym}_{unit}_1"\n    ' + "\n    ".join(body + pins) + "\n  )")
                items.append(self.place(ci, f"ALT:{sym}", ref, unit))
            libs.append(
                f'(symbol "ALT:{sym}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
                f'  (property "Reference" {q(prefix)} (at 0 0 0) {FONT})\n'
                f'  (property "Value" {q(self.value(first))} (at 0 0 0) {FONT})\n'
                f'  (property "Footprint" {q(self.footprint(first))} (at 0 0 0) {HIDDEN})\n'
                f'  (property "Datasheet" "" (at 0 0 0) {HIDDEN})\n'
                f'  (property "Description" {q(self.comps[first].get("COMPONENTDESCRIPTION", ""))} (at 0 0 0) {HIDDEN})\n'
                + "\n".join(units) + "\n)")

        libs += self.power_ports(items)
        items += self.wiring()
        items += self.sheet_graphics()
        return (
            f'(kicad_sch (version 20260306) (generator "altium_sch_import") (generator_version "10.0")\n'
            f'  (uuid "{self.root}")\n  (paper "{self.paper}")\n'
            f'  (title_block (title {q(self.name)}) (comment 1 "Converted from the authors\' Altium schematic by altium_sch_import.py"))\n'
            f'  (lib_symbols\n' + "\n".join(libs) + "\n  )\n" + "\n".join(items) +
            '\n  (sheet_instances (path "/" (page "1")))\n)\n')

    def place(self, ci: int, lib_id: str, ref: str, unit: int) -> str:
        comp = self.comps[ci]
        here = self.at(point(comp))
        des = self.children(ci, ("34",))
        ref_at = self.at(point(des[0])) if des else here
        com = self.parameter(ci, "Comment")
        val_at = self.at(point(com)) if com and "LOCATION.X" in com else here
        val_fx = HIDDEN if (com is None or com.get("ISHIDDEN") == "T") else FONT
        dnp = "yes" if self.value(ci).strip().upper() == "DNP" else "no"
        return (
            f'(symbol (lib_id {q(lib_id)}) (at {here} 0) (unit {unit}) (exclude_from_sim no) (in_bom yes) '
            f'(on_board yes) (dnp {dnp}) (uuid "{uid()}")\n'
            f'  (property "Reference" {q(ref)} (at {ref_at} 0) {FONT})\n'
            f'  (property "Value" {q(self.value(ci))} (at {val_at} 0) {val_fx})\n'
            f'  (property "Footprint" {q(self.footprint(ci))} (at {here} 0) {HIDDEN})\n'
            f'  (property "Datasheet" "" (at {here} 0) {HIDDEN})\n'
            f'  (property "Description" {q(comp.get("COMPONENTDESCRIPTION", ""))} (at {here} 0) {HIDDEN})\n'
            f'  (property "Altium library reference" {q(comp.get("LIBREFERENCE", ""))} (at {here} 0) {HIDDEN})\n'
            f'  (instances (project {q(self.name)} (path "/{self.root}" (reference {q(ref)}) (unit {unit}))))\n)')

    def power_ports(self, items: list[str]) -> list[str]:
        """Each Altium power port becomes a KiCad power symbol naming its net."""
        libs: dict[str, str] = {}
        ports = [r for r in self.recs if r.get("RECORD") == "17"]
        for n, r in enumerate(ports, 1):
            net = r.get("TEXT", "")
            o = int(r.get("ORIENTATION", 0)) % 4
            style = r.get("STYLE", "0")
            sym = f"PWR_{safe(net)}_{style}_{o}"
            dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][o]
            stem, half = 10 * FRAC, 5 * FRAC           # 100 mil stem, 100 mil wide bar
            tip = (dx * stem, dy * stem)
            a = (tip[0] - dy * half, tip[1] + dx * half)
            b = (tip[0] + dy * half, tip[1] - dx * half)
            label = (tip[0] + dx * 3 * FRAC - (half if dy else 0), tip[1] + (dy * 3 * FRAC if dy > 0 else dy * 8 * FRAC))
            if sym not in libs:
                libs[sym] = (
                    f'(symbol "ALT:{sym}" (power) (pin_numbers (hide yes)) (pin_names (offset 0) (hide yes)) '
                    f'(exclude_from_sim no) (in_bom no) (on_board yes)\n'
                    f'  (property "Reference" "#PWR" (at 0 0 0) {HIDDEN})\n'
                    f'  (property "Value" {q(net)} (at {mm(label[0])} {mm(label[1])} 0) {FONT})\n'
                    f'  (property "Footprint" "" (at 0 0 0) {HIDDEN})\n'
                    f'  (property "Datasheet" "" (at 0 0 0) {HIDDEN})\n'
                    f'  (property "Description" {q("Power port " + net + " from the Altium schematic")} (at 0 0 0) {HIDDEN})\n'
                    f'  (symbol "{sym}_0_1"\n'
                    f'    (polyline (pts (xy 0 0) (xy {mm(tip[0])} {mm(tip[1])})) {STROKE} (fill (type none)))\n'
                    f'    (polyline (pts (xy {mm(a[0])} {mm(a[1])}) (xy {mm(b[0])} {mm(b[1])})) {STROKE} (fill (type none)))\n  )\n'
                    f'  (symbol "{sym}_1_1"\n'
                    f'    (pin power_in line (at 0 0 0) (length 0) (name {q(net)} (effects (font (size {TEXT_MM} {TEXT_MM})))) '
                    f'(number "1" (effects (font (size {TEXT_MM} {TEXT_MM})))))\n  )\n)')
            here = self.at(point(r))
            lx, ly = point(r)[0] + label[0], point(r)[1] + label[1]
            ref = f"#PWR{n:03d}"
            items.append(
                f'(symbol (lib_id "ALT:{sym}") (at {here} 0) (unit 1) (exclude_from_sim no) (in_bom no) (on_board yes) '
                f'(dnp no) (uuid "{uid()}")\n'
                f'  (property "Reference" "{ref}" (at {here} 0) {HIDDEN})\n'
                f'  (property "Value" {q(net)} (at {self.sx(lx)} {self.sy(ly)} 0) {FONT})\n'
                f'  (property "Footprint" "" (at {here} 0) {HIDDEN})\n'
                f'  (property "Datasheet" "" (at {here} 0) {HIDDEN})\n'
                f'  (property "Description" "" (at {here} 0) {HIDDEN})\n'
                f'  (instances (project {q(self.name)} (path "/{self.root}" (reference "{ref}") (unit 1))))\n)')
        return list(libs.values())

    def wiring(self) -> list[str]:
        """Wires, junctions and net labels. Altium joins a wire to anything
        that touches it along its length; KiCad joins at wire ends, so every
        wire is cut wherever a wire end, pin, port, label or junction sits on it."""
        segments = []
        for r in self.recs:
            if r.get("RECORD") == "27":
                pts = points(r)
                segments += [(a, b) for a, b in itertools.pairwise(pts) if a != b]
        manual = [point(r) for r in self.recs if r.get("RECORD") == "29"]
        labels = [r for r in self.recs if r.get("RECORD") == "25"]
        pin_ends = [self.pin_end(p) for ci in self.comps for p in self.children(ci, ("2",)) if self.shown(ci, p)]
        ports = [point(r) for r in self.recs if r.get("RECORD") == "17"]
        touch = set(manual) | set(pin_ends) | set(ports) | {point(r) for r in labels}
        for a, b in segments:
            touch |= {a, b}

        def inside(p, a, b) -> bool:
            if p in (a, b):
                return False
            cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            return (cross == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                    and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))

        pieces = []
        for a, b in segments:
            cuts = sorted((p for p in touch if inside(p, a, b)),
                          key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            chain = [a] + cuts + [b]
            pieces += list(itertools.pairwise(chain))
        pieces = list(dict.fromkeys((min(s), max(s)) for s in pieces))

        ends: dict[tuple[int, int], int] = defaultdict(int)
        for a, b in pieces:
            ends[a] += 1
            ends[b] += 1
        others = defaultdict(int)
        for p in pin_ends + ports:
            others[p] += 1
        out = [f'(wire (pts (xy {self.at(a)}) (xy {self.at(b)})) (stroke (width 0) (type default)) (uuid "{uid()}"))'
               for a, b in pieces]
        for p, n in sorted(ends.items()):
            if n >= 3 or (n == 2 and others[p]):
                out.append(f'(junction (at {self.at(p)}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')
        for r in labels:
            rot = (int(r.get("ORIENTATION", 0)) % 4) * 90
            out.append(f'(label {q(r.get("TEXT", ""))} (at {self.at(point(r))} {rot}) {FONT} (uuid "{uid()}"))')
        return out

    def sheet_graphics(self) -> list[str]:
        """Drawing-only objects that belong to no component (notes, title block)."""
        out = []
        for r in self.recs:
            if self.owned_by_component(r):
                continue
            kind = r.get("RECORD")
            if kind in ("6", "13"):
                pts = points(r) if kind == "6" else [point(r), point(r, "CORNER")]
                if len(pts) >= 2:
                    out.append(f"(polyline (pts {' '.join('(xy ' + self.at(p) + ')' for p in pts)}) "
                               f'(stroke (width 0) (type default)) (uuid "{uid()}"))')
            elif kind == "4" and r.get("TEXT"):
                rot = (int(r.get("ORIENTATION", 0)) % 4) * 90
                out.append(f'(text {q(r["TEXT"])} (at {self.at(point(r))} {rot}) {FONT} (uuid "{uid()}"))')
        return out


# ---------------------------------------------------------------- checking

BOARD_NETS = r"""
import json, sys, pcbnew
board = pcbnew.LoadBoard(sys.argv[1])
out = {}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNumber():
            out.setdefault(fp.GetReference(), {})[pad.GetNumber()] = pad.GetNetname()
print(json.dumps(out))
"""


def schematic_nets(netlist: pathlib.Path) -> dict[str, dict[str, str]]:
    """ref -> pin -> net, read from a kicad-cli s-expression netlist."""
    text = netlist.read_text()
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for block in re.split(r"\(net\s+\(code\s", text)[1:]:
        name = re.search(r'\(name\s+"((?:[^"\\]|\\.)*)"\)', block).group(1)
        for ref, pin in re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', block):
            out[ref][pin] = name
    return out


def compare(sch: dict, pcb: dict) -> dict:
    """Do the schematic and the board join the same pins together? Net names
    are ignored; a net is the set of pins on it."""
    def groups(side, pins):
        g = defaultdict(set)
        for ref, pin in pins:
            net = side[ref][pin]
            g[net if net else f"unconnected {ref}.{pin}"].add(f"{ref}.{pin}")
        return g

    sch_pins = {(r, p) for r, pins in sch.items() for p in pins}
    pcb_pins = {(r, p) for r, pins in pcb.items() for p in pins}
    common = sch_pins & pcb_pins
    gs, gp = groups(sch, common), groups(pcb, common)
    same = {frozenset(v) for v in gs.values()} & {frozenset(v) for v in gp.values()}
    differ = [{"schematic_net": n, "pins": sorted(v)} for n, v in sorted(gs.items()) if frozenset(v) not in same]
    return {
        "components_in_schematic": len(sch), "components_on_board": len(pcb),
        "only_in_schematic": sorted(set(sch) - set(pcb)), "only_on_board": sorted(set(pcb) - set(sch)),
        "pins_compared": len(common),
        "pins_only_in_schematic": sorted(f"{r}.{p}" for r, p in sch_pins - pcb_pins if r in pcb),
        "pins_only_on_board": sorted(f"{r}.{p}" for r, p in pcb_pins - sch_pins if r in sch),
        "nets_in_schematic": len(gs), "nets_on_board": len(gp), "nets_identical": len(same),
        "nets_that_differ": differ,
    }


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, check=False)


def check(board: str, sch_path: pathlib.Path) -> dict:
    folder = sch_path.parent
    net = folder / f"{board}.net"
    r = run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch_path])
    result: dict = {"loads_in_kicad_cli": r.returncode == 0, "netlist_rc": r.returncode}
    if r.returncode != 0:
        result["error"] = (r.stdout + r.stderr).strip()[-400:]
        return result
    erc = folder / f"{board}_erc.json"
    e = run([KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", erc, sch_path])
    if erc.exists():
        counts: dict[str, int] = defaultdict(int)
        for sheet in json.loads(erc.read_text()).get("sheets", []):
            for v in sheet.get("violations", []):
                counts[f'{v.get("severity")}:{v.get("type")}'] += 1
        result["erc"] = dict(sorted(counts.items()))
    result["erc_rc"] = e.returncode
    p = run([KICAD_CLI, "sch", "export", "pdf", "-o", folder / f"{board}_sch.pdf", sch_path])
    result["pdf_rc"] = p.returncode
    b = run([KICAD_PY, "-c", BOARD_NETS, folder / f"{board}.kicad_pcb"])
    if b.returncode != 0:
        result["board_error"] = b.stderr.strip()[-400:]
        return result
    result["against_board"] = compare(schematic_nets(net), json.loads(b.stdout.strip().splitlines()[-1]))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="netlist, ERC, PDF and comparison with the board")
    ap.add_argument("boards", nargs="*", default=list(BOARDS), help="board folders to convert")
    args = ap.parse_args()
    failed = 0
    for board in args.boards:
        src = ELEC / BOARDS[board]
        out = HERE / board / f"{board}.kicad_sch"
        sheet = Sheet(read_records(src), board)
        out.write_text(sheet.build(), encoding="utf-8")
        line = f"{board}: {len(sheet.comps)} components, paper {sheet.paper} -> {out.relative_to(ELEC.parent)}"
        if args.check:
            res = check(board, out)
            (HERE / board / "sch_check.json").write_text(json.dumps(res, indent=1) + "\n")
            cmp_ = res.get("against_board", {})
            line += (f" | loads {res['loads_in_kicad_cli']} | nets identical {cmp_.get('nets_identical')}"
                     f" of {cmp_.get('nets_in_schematic')} (board {cmp_.get('nets_on_board')})")
            failed += not res["loads_in_kicad_cli"]
        print(line)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
