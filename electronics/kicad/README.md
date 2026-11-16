# KiCad imports (added in this fork)

The six Altium boards, imported into KiCad so they open without Altium. One folder per board, each with the
`.kicad_pcb`, a top-side render, the importer's report and a statistics file.

Made with `kicad-cli pcb import --format altium` from KiCad 10.0.3, so the files are in KiCad 10 format and
need KiCad 10 or newer. Every board imported with return code 0 and no importer errors, then loaded again
for a design-rule check and a 3D render.

| Board | Source | Copper layers | Thickness mm | Size mm | Footprints | Min track / gap mm | Smallest via drill mm |
|---|---|---|---|---|---|---|---|
| `motor_driver_v3` (the robot's main board) | `Motor driver v3/PCB_motor_driver_v3.PcbDoc` | 4 | 0.57 | 23.2 x 22.2 | 69 | 0.127 / 0.127 | 0.2 |
| `ir_encoder_v2` | `IR encoder/PCB_IR_Encoder_v2.PcbDoc` | 2 | 0.41 | 10.1 x 6.4 | 7 | 0.254 / 0.127 | 0.2 |
| `encoder_flex_cable` | `IR encoder/PCB_Flex_cable_Encoder.PcbDoc` | 2 | 0.14 | 9.1 x 8.7 | 8 | n/a | none |
| `encoder_wheel` | `Encoder wheel/PCB_Encoder_v2_single_16.PcbDoc` | 2 | 0.41 | 9.4 x 9.4 | 3 | n/a | 1.0 |
| `master_board` (USB base station) | `master board/PCB_rovables_master_v1.PcbDoc` | 2 | 1.49 | 45.3 x 39.4 | 17 | 0.406 / 0.254 | 0.9 |
| `programming_shield` | `Programming adapter/PCB_Shield_for_Rovables_v2.PcbDoc` | 2 | 0.41 | 18.2 x 36.1 | 6 | 0.152 / 0.152 | 0.2 |

Known gaps:

- `motor_driver_v3` and `encoder_flex_cable` imported with degenerate sub-micron segments and micro-gaps on Edge.Cuts; those were cleaned and snapped into closed outlines so both boards report `has_outline: true` and plot cleanly.
- The design-rule check reports violations on every board (motor driver 1144, shield 553, master 146, encoder 60, flex 56, wheel 42). They are almost all KiCad's default rules being stricter than the 0.127 mm tracks and 0.2 mm vias these boards were drawn with; no board has unconnected nets.
- The importer skipped Altium's unused internal plane layers on every board.

## Schematics

The four Altium schematics are converted too: `<board>/<board>.kicad_sch`, with a PDF and a PNG of the sheet
beside each. KiCad 10.0.3 imports an Altium schematic only from the schematic editor's window (File, Import,
Non-KiCad Schematic) and `kicad-cli` has no schematic import, so `altium_sch_import.py` in this folder reads the
`.SchDoc` records directly and writes the KiCad file. Each placed component becomes its own symbol drawn from
the Altium graphics, with the wires, junctions, net labels and power ports carried over. Rebuild and re-check
with `python3 electronics/kicad/altium_sch_import.py --check`.

The check loads each schematic with `kicad-cli`, exports its netlist and compares it pin by pin with the nets
on the imported board (`sch_check.json` in each folder; net names are ignored, a net is the set of pins on it).

| Schematic | Components | Loads in kicad-cli | Pins compared with the board | Nets identical |
|---|---|---|---|---|
| `motor_driver_v3` | 58 | yes | 241 | 75 of 76 |
| `ir_encoder_v2` | 6 | yes | 17 | 6 of 6 |
| `programming_shield` | 6 | yes | 61 | 24 of 25 |
| `master_board` | 14 | yes | 100 | 34 of 34 |

The two nets that differ are differences between the authors' own schematic and board, not conversion faults:

- Motor driver, VBAT: the schematic joins C23.1, U4.3, connector P4 pin 1 and the on/off switch SW1. On the
  board the switch footprint is named `*1`, and P4 pin 1 is not on VBAT.
- Programming shield, RESET: the schematic puts P4 pin 1 on RESET with P1.10, P5.10 and P6.4; the board does not.

Limits of the conversion: there is no flex-cable or encoder-wheel schematic in the authors' files, so those
two boards have none. Footprint names are the Altium ones and are not linked to the KiCad footprints on the
boards. The electrical rules check reports unconnected pins and undriven power pins the Altium sheets also
have (counts in each `sch_check.json`), plus library warnings because the symbols live inside the schematic.
The embedded logo image and the title-block field values are not carried over. The authors' schematic PDFs
still sit next to each `.SchDoc`.
