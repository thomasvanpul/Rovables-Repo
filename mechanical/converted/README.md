# Converted CAD (added in this fork)

The authors' SolidWorks 2016 parts, converted so they open without SolidWorks. Geometry is theirs, unchanged.

- `step/` one STEP file per part, for any CAD package.
- `stl/` the same parts as meshes, in the orientation they were modelled in. Print-oriented copies are in `/printables/stl`.
- `preview/` a picture of each part, and `fusion_all_parts.png` with the robot parts side by side.

How: the `.SLDPRT` files from the two zips under `mechanical/` were uploaded to Autodesk Fusion (build 2706.1.17),
which translates SolidWorks files on its servers, then exported as STEP and high-refinement binary STL.
Each part came through as one solid body, and its volume matches the STL the authors shipped where one exists
(for example `BB_Mg Adapter V2`: 114.1 mm3 here, 114.0 mm3 in theirs).

Converted: the eleven custom parts. Robot: `base_plate_v1`, `bottom_ski_v1`, `case_minimum_covered`,
`BB_Mg_Adapter_V2`, `Mt_Mg_Adapter_V2`, `Magnet_Holder_V1C`, `rubber_wheels_v1`, `Chassis_encoder_inside_v2`
(the earlier chassis). Controller: `top_part_joystick_v1`, `bottom_part_joystick_v1`, `radio_dungle`.

Not converted, because they are bought parts or circuit-board models with nothing to make: the screws, nut,
standoffs, bearing, magnet, battery, motor (`TGPP06-D-136`), connectors, and the board assemblies exported from
Altium (`*PCB_motor_driver_v3*`, `PCB_IR_Encoder_v2_6`, `Teensy_3-2`, joystick, switches). They are still in the zips.
The three `.SLDASM` assemblies were not converted either; `mechanical/Assembly_rev1.pdf` shows how the parts go together.
