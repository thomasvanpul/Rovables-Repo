# Printables (added in this fork)

The authors printed these parts on a Formlabs resin printer at 25 micron (see `mechanical/BOM_assembly.xlsx`).
This folder is an attempt to print them on an ordinary FDM printer (Bambu P1S, PLA). Nothing here has been
printed yet. The geometry is the authors' own, unchanged: each part is only rotated onto a printable face.

Rebuild everything with `python3 printables/build_printables.py --slice` (needs trimesh and Bambu Studio;
parameters are at the top of the script). `parts.json` holds the measured numbers this page quotes.

## Plates

| File | Printer setup | Contents | Time | Filament |
|---|---|---|---|---|
| `plates/rovables_all_P1S_0.4mm.3mf` | P1S, 0.4 mm nozzle, 0.12mm Fine @BBL X1C, 3 Arachne walls, 20% gyroid, tree supports, PLA | everything below, 19 objects, one plate | 3 h 35 min | 57.55 g |
| `plates/rovables_robot_P1S_0.2mm.3mf` | P1S, 0.2 mm nozzle, 0.10mm Standard @BBL X1C 0.2 nozzle, Arachne walls, tree supports, PLA | robot parts only, 16 objects, one plate | 2 h 22 min | 8.08 g |

Time and grams are Bambu Studio's own estimates from the slice (both sliced with return code 0, no slicer warnings).
Both plates hold parts for 2 robots.

Use the 0.2 mm plate for the robot if the printer has a 0.2 mm nozzle fitted. The wheel hubs have 0.75 mm walls
and a 0.33 mm rim, which is under two extrusion lines on a 0.4 mm nozzle, so the 0.4 mm plate may print them
badly or not at all. The joystick enclosure is fine on 0.4 mm. Whether either plate gives usable robot parts is
not known until one is printed.

## How much of each part the slice prints

A slicer leaves out what it cannot fit and still reports success, so `slice_check.py` reads the G-code in a
plate and compares the plastic laid down as model (not supports or brim) with each part's volume. Run it with
`python3 printables/slice_check.py printables/plates/*.3mf`.

| Part | 0.4 mm plate, classic walls (first slice) | 0.4 mm plate, Arachne | 0.2 mm plate, classic (first slice) | 0.2 mm plate, Arachne |
|---|---|---|---|---|
| `base_plate_v1` | 0.96 | 0.96 | 0.97 | 0.97 |
| `bottom_ski_v1` | 0.98 | 0.97 | 0.96 | 0.96 |
| `case_minimum_covered` | 1.01 | 0.98 | 0.97 | 0.97 |
| `BB_Mg_Adapter_V2` | 1.00 | 0.95 | 1.00 | 0.96 |
| `Mt_Mg_Adapter_V2` | 1.01 | 0.98 | 0.97 | 0.96 |
| `Magnet_Holder_V1C` | 1.47 | 0.97 | 0.97 | 0.95 |
| `Chassis_encoder_inside_v2` | 0.98 | 0.97 | not on it | not on it |
| `top_part_joystick_v1` | 0.83 | 0.80 | not on it | not on it |
| `bottom_part_joystick_v1` | 0.88 | 0.85 | not on it | not on it |

The plates were first sliced with the profiles' default "classic" walls. On the 0.4 mm nozzle that laid the
4 mm magnet rod down at 147% of its drawn volume, so its magnet seats would have come out wrong. Both plates
are now sliced with Arachne walls, which vary the line width; every robot part lands between 95% and 98%.
The joystick halves are lower because they are thick enough to have 20% infill inside.

This is a volume check. It shows no part is being skipped or fattened; it cannot show whether a 0.33 mm rim
came out as a clean wall. Only a print does that.

## Parts

Sizes are as oriented for printing. Grams is the part printed solid in PLA (1.24 g/cm3), so an upper bound;
the slicer's figure for a whole plate is in the table above.

| STL (in `stl/`) | What it is | Copies on the 0.4 mm plate | Size mm | Solid g |
|---|---|---|---|---|
| `base_plate_v1.stl` | Main body (chassis): carries both motors, bearings, encoder boards and standoffs | 2 | 23.95 x 25.16 x 11.0 | 1.02 |
| `bottom_ski_v1.stl` | Undercarriage: clamps the two motors into the main body from below | 2 | 9.99 x 18.36 x 2.7 | 0.22 |
| `case_minimum_covered.stl` | Cover over the electronics and battery | 2 | 23.95 x 26.46 x 11.2 | 1.22 |
| `BB_Mg_Adapter_V2.stl` | Ball bearing adapter: idler-side wheel hub, holds the ring magnets | 4 | 9.5 x 9.5 x 6.0 | 0.14 |
| `Mt_Mg_Adapter_V2.stl` | Motor adapter: driven-side wheel hub on the motor shaft, holds the ring magnets | 4 | 9.5 x 9.5 x 3.9 | 0.12 |
| `Magnet_Holder_V1C.stl` | Rod for magnets: goes behind the fabric with a ring magnet on each end | 2 | 4.0 x 4.0 x 31.0 | 0.3 |
| `Chassis_encoder_inside_v2.stl` | Earlier chassis with the encoders inside (assemblies v1 to v3); one copy for comparison | 1 | 25.75 x 24.8 x 15.45 | 1.38 |
| `top_part_joystick_v1.stl` | Joystick controller enclosure, top | 1 | 123.06 x 62.8 x 21.5 | 28.2 |
| `bottom_part_joystick_v1.stl` | Joystick controller enclosure, bottom | 1 | 123.04 x 62.78 x 13.0 | 26.79 |
| `rubber_wheels_v1.stl` | Tyre. The paper used 1 mm neoprene; print in TPU or cut from sheet, not PLA | not plated | 10.9 x 10.9 x 3.5 | 0.17 |
| `radio_dungle.stl` | Model of the bought USB radio dongle, for fit only; not a printed part | not plated | 15.0 x 7.3 x 29.0 | 0.87 |

All 11 STLs are watertight (checked with trimesh after export). `case_minimum_covered` came out of
the CAD export with two pinholes, filled with two triangles; the others needed no repair.

Not printed in PLA: `rubber_wheels_v1` is the tyre (the paper used 1 mm neoprene; TPU or cut sheet), and
`radio_dungle` is a model of the bought USB radio, there for fit only.

## Bought parts the prints need

From `mechanical/BOM_assembly.xlsx`, per robot: 2 M2 x 7 mm standoffs, 2 M2 x 4 mm standoffs, 6 M2 x 3 mm screws,
2 M1.6 x 3 mm screws and nuts, 4 ring magnets 3/8 x 1/8 x 1/16 in and 2 of 3/8 x 1/8 x 1/8 in (K&J Magnetics),
2 bearings 4 x 8 x 3 mm, 2 TGPP06-D-136 gear motors, a 100 mAh LiPo.
