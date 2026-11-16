#!/usr/bin/env python3
"""Rovables BOM: merge the boards' part lists and look each part up in the JLCPCB assembly library.

    python3 electronics/bom/check_availability.py

Writes bom_all_boards.csv and availability.json next to this file. The motor driver list is the
authors' own spreadsheet; the other boards had no BOM file, so their rows come from the component
values on the boards as imported into KiCad (electronics/kicad), and a part number marked
ASSUMED is a guess at an unspecified part, to be confirmed against the schematic PDF.
Stock and prices are whatever JLCPCB's public parts search returns at run time.
"""
from __future__ import annotations

import csv
import datetime
import json
import math
import pathlib
import time
import urllib.request

import openpyxl

# ---------------------------------------------------------------- parameters
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MOTOR_BOM = ROOT / "electronics" / "Motor driver v3" / "BOM_motor_driver_V3.xlsx"
SETS = 2                       # robots to build
JLC_MIN_ASSEMBLY = 2           # JLCPCB's smallest assembly quantity for standard PCBA
JLC_SEARCH = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
PAUSE_S = 0.5                  # between lookups
BOARDS_PER_SET = {"motor_driver_v3": 1, "ir_encoder_v2": 2, "master_board": 0.5, "programming_shield": 0.5}
# Boards with no BOM file: (board, designators, value on the board, part number, assumed?)
EXTRA = [
    ("ir_encoder_v2", "U5", "GP2S60 reflective IR sensor", "GP2S60B", False),
    ("ir_encoder_v2", "U1", "N-channel MOSFET, SOT-323", "2N7002W", True),
    ("ir_encoder_v2", "P3", "0.5 mm 4-way FPC connector", "FH33J-4S-0.5SH(99)", False),
    ("ir_encoder_v2", "R1", "100R 0603", "RC0603FR-07100RL", True),
    ("ir_encoder_v2", "R2, R3", "10K 0603", "RC0603FR-0710KL", True),
    ("master_board", "U1", "Teensy 3.2 (base station MCU board)", "TEENSY 3.2", False),
    ("master_board", "P5, P6, P7, P8", "JST SH 4-way top entry", "BM04B-SRSS-TB", False),
    ("master_board", "L1", "LED blue 1206", "19-217/BHC-ZL1M2RY/3T", True),
    ("master_board", "L2", "LED red 1206", "KT-1206R", True),
    ("master_board", "R1, R2", "300R 1206", "RC1206FR-07300RL", True),
    ("master_board", "C?", "100uF 25V electrolytic SMD", "VZH101M1ETR-0606", True),
    ("programming_shield", "P4", "DF12 20-way board-to-board, mates with the robot", "DF12(4.0)-20DS-0.5V(86)", False),
    ("programming_shield", "P3", "Micro-B USB receptacle SMT", "10118194-0001LF", True),
]
# ---------------------------------------------------------------------------


def motor_rows() -> list[dict]:
    ws = openpyxl.load_workbook(MOTOR_BOM, data_only=True).active
    rows = []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not r[6]:
            continue
        rows.append({"board": "motor_driver_v3", "designators": str(r[2]), "value": f"{r[0]} ({r[3]})",
                     "qty_per_board": int(r[4]), "mpn": str(r[6]).strip(), "assumed": False,
                     "digikey": str(r[8] or "")})
    return rows


def extra_rows() -> list[dict]:
    return [{"board": b, "designators": d, "value": v, "qty_per_board": len(d.split(",")), "mpn": m,
             "assumed": a, "digikey": ""} for b, d, v, m, a in EXTRA]


def lookup(mpn: str) -> dict:
    body = json.dumps({"keyword": mpn, "currentPage": 1, "pageSize": 10}).encode()
    req = urllib.request.Request(JLC_SEARCH, data=body, headers={"Content-Type": "application/json",
                                                                 "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as f:
            found = (json.load(f).get("data") or {}).get("componentPageInfo", {}).get("list") or []
    except Exception as e:  # noqa: BLE001  network errors are reported per row, not fatal
        return {"status": f"lookup failed: {e}"}
    key = mpn.lower().replace(" ", "")
    exact = [c for c in found if (c.get("componentModelEn") or "").lower().replace(" ", "") == key]
    if not exact:
        return {"status": "not in the JLCPCB library", "nearest": [c.get("componentModelEn") for c in found[:3]]}
    c = max(exact, key=lambda c: c.get("stockCount") or 0)
    prices = sorted((p.get("startNumber") or 0, p.get("productPrice")) for p in c.get("componentPrices") or [])
    return {"status": "in stock" if (c.get("stockCount") or 0) > 0 else "listed, zero stock",
            "lcsc": c.get("componentCode"), "stock": c.get("stockCount") or 0,
            "library": c.get("componentLibraryType"), "unit_usd": prices[0][1] if prices else None,
            "package": c.get("componentSpecificationEn")}


def main() -> None:
    rows = motor_rows() + extra_rows()
    for r in rows:
        r.update(lookup(r["mpn"]))
        r["qty_for_sets"] = math.ceil(r["qty_per_board"] * BOARDS_PER_SET[r["board"]] * SETS)
        print(f"{r['board']:18s} {r['mpn']:28s} {r['status']:26s} {r.get('lcsc') or '':10s} "
              f"stock={r.get('stock', '')} usd={r.get('unit_usd', '')}")
        time.sleep(PAUSE_S)
    cols = ["board", "designators", "value", "qty_per_board", "qty_for_sets", "mpn", "assumed", "digikey",
            "status", "lcsc", "stock", "library", "unit_usd", "package", "nearest"]
    with open(HERE / "bom_all_boards.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    (HERE / "availability.json").write_text(json.dumps(
        {"checked": datetime.datetime.now().astimezone().isoformat(timespec="minutes"), "source": JLC_SEARCH,
         "sets": SETS, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
