# Where v2 starts from: the magnet crawler test, 16 Nov 2026

v2 was not drawn from the paper alone. On 16 Nov 2026 a one-roller test rig went through five versions in a
morning. The v3 was printed and handled, and v4 is the answer to what that print showed. This file records what
the test showed and, just as plainly, what it did not.

## What was built

| Version | Change | Why |
|---|---|---|
| v0 | Two SG90 servos, each driving a 14 mm roller with a magnet in it; two free magnets behind the fabric | First layout, copied from Rovables: the magnets are the wheels |
| v1 | N20 gear motors in place of the servos; 11.8 mm rollers | N20s were on hand, and the smaller roller brings the magnet 1.8 mm from the fabric instead of 2.9 |
| v2 | One magnet fixed in the chassis, one loose inside the shirt, two plain wheels | Nothing inside the shirt except one magnet cylinder |
| v3 | The chassis magnet becomes the driven roller, turned from both ends by two N20s | See the finding below |
| v4 | 9.2 mm bore, 12 mm roller, a floor and an end cap for each motor | Fixes from the v3 print |

`crawler_v4_geom.py` in this folder is the v4 geometry as it was sent to print, and `crawler_v4_fusion.png`
is how it looked in Fusion.

## What it showed

1. **The clamp force has to land on a wheel.** In the crawler's v2 the loose magnet pulled the fabric up against
   the fixed chassis floor. The whole clamp force became sliding drag and the wheels carried almost none of it.
   Making the magnet itself the roller turns the clamp force into the roller's grip, and both faces of the fabric
   only roll. This is why the Rovable v2 has no fixed magnet anywhere: each magnet is inside a driven roller.
2. **Measure the stock.** The "8 x 25 mm" N42 rods measured 8.92 mm across with calipers. The v3 capsule,
   drawn for 8 mm, was too small. v4 and the Rovable v2 use a 9.2 mm bore.
3. **Cover the motors.** v3 left the N20s open. v4 added a floor under each motor and a snap-in end cap with a
   wire slot. The Rovable v2 keeps both.
4. **Fits that printed.** The 12.2 x 10.2 mm tunnel for the N20 body, the D hole for its 3 mm shaft and the
   1.4 mm roller wall were in the v3 print, and no fault was recorded against them. They are marked PRINTED in
   `../cad/rovable_v2_geom.py`. The values v4 changed (the 9.2 mm bore, the motor floor and cap) are marked V4:
   no print result is on record for them.

## What it did not show

No number was recorded for any of these, so none is claimed:

- how hard the roller holds on a shirt, or how much it can pull;
- whether two N20s at the voltage used can turn the roller against the clamp;
- how it behaves over a seam, on a sleeve, or on a curved part of the body;
- anything about steering. The test rig has one roller and goes in a straight line only.

The first job for a printed Rovable v2 is to put numbers on that list.
