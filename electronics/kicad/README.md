# KiCad imports (added in this fork)

The six Altium boards, imported into KiCad so they open without Altium. One folder per board, each with the
`.kicad_pcb`, a top-side render, the importer's report and a statistics file.

Made with `kicad-cli pcb import --format altium` from KiCad 10.0.3, so the files are in KiCad 10 format and
need KiCad 10 or newer. Every board imported with return code 0 and no importer errors, then loaded again
for a design-rule check and a 3D render.

| Board | Source | Copper layers | Thickness mm | Size mm | Footprints | Min track / gap mm | Smallest via drill mm |
|---|---|---|---|---|---|---|---|
| `motor_driver_v3` (the robot's main board) | `Motor driver v3/PCB_motor_driver_v3.PcbDoc` | 4 | 0.57 | about 24 x 19 (copper extent) | 69 | 0.127 / 0.127 | 0.2 |
| `ir_encoder_v2` | `IR encoder/PCB_IR_Encoder_v2.PcbDoc` | 2 | 0.41 | 10.1 x 6.4 | 7 | 0.254 / 0.127 | 0.2 |
| `encoder_flex_cable` | `IR encoder/PCB_Flex_cable_Encoder.PcbDoc` | 2 | 0.14 | about 8 x 2.5 (copper extent) | 8 | n/a | none |
| `encoder_wheel` | `Encoder wheel/PCB_Encoder_v2_single_16.PcbDoc` | 2 | 0.41 | 9.4 x 9.4 | 3 | n/a | 1.0 |
| `master_board` (USB base station) | `master board/PCB_rovables_master_v1.PcbDoc` | 2 | 1.49 | 45.3 x 39.4 | 17 | 0.406 / 0.254 | 0.9 |
| `programming_shield` | `Programming adapter/PCB_Shield_for_Rovables_v2.PcbDoc` | 2 | 0.41 | 18.2 x 36.1 | 6 | 0.152 / 0.152 | 0.2 |

Known gaps, none of them fixed here:

- `motor_driver_v3` and `encoder_flex_cable` have no closed board outline on Edge.Cuts after import (the outline
  sits on an Altium mechanical layer), so their size above is the extent of the copper, and the outline has to be
  redrawn before KiCad can plot fabrication files. The authors' Gerber zips are untouched and still usable.
- The design-rule check reports violations on every board (motor driver 1182, shield 553, master 146, flex 64,
  encoder 60, wheel 42). They are almost all KiCad's default rules being stricter than the 0.127 mm tracks and
  0.2 mm vias these boards were drawn with; no board has unconnected nets.
- The importer skipped Altium's unused internal plane layers on every board.
- The four schematics (`.SchDoc`) are not imported. KiCad 10.0.3 has no command-line schematic import; it is
  File, Import, Non-KiCad Schematic in the schematic editor, one file at a time. The authors' schematic PDFs sit
  next to each `.SchDoc`.
