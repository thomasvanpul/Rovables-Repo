# Parts list and availability (added in this fork)

`bom_all_boards.csv` is one parts list for all the boards, with stock and price for each line. Rebuild it with
`python3 electronics/bom/check_availability.py`.

Where the rows come from: the motor driver (the robot's main board) uses the authors' own
`Motor driver v3/BOM_motor_driver_V3.xlsx`, 41 lines. The other boards had no parts list, so their rows are the
component values read off the boards (see `electronics/kicad`); a row marked `assumed` names a part the board
does not specify, such as "N-channel MOSFET, SOT-323", and needs checking against the schematic PDF.

Stock and prices were read from JLCPCB's assembly parts library on 16 November 2026 (the time is in
`availability.json`). Mouser was not checked: its site refuses automated requests (tried again from a browser on 16 November,
connection aborted).

## What it found, motor driver (41 lines)

- 30 lines in stock. Five of them thinly: ATSAMD21G18A-AUT (6), MCP6422-E/MS (2), TPSR106K006R1000 (2),
  TL8A0107M6R3C (10), GRM188R60G106ME47D (16).
- 8 lines listed with zero stock, including the ones the board cannot do without: nRF24L01P-R7 (radio),
  DRV8835DSSR (motor driver), FH33J-4S-0.5SH(99) and DF12D(4.0)-20DP-0.5V(81) (connectors), 2450BM14A0002T (balun).
  LCSC's own site also showed zero for the radio, the motor driver and the FH33J on the same day.
- 3 lines not in the library: the two Panasonic LEDs LNJ947W8CRA and LNJ437W84RA, and resistor ERJ-3EKF4991V.
  All three have ordinary equivalents.
- Parts for one board come to USD 51.00 for the 38 priced lines. The MPU-6050 is USD 21.00 of that.

The other boards: the IR encoder's sensor (GP2S60B) is in stock at USD 0.40; a Teensy 3.2, the JST BM04B-SRSS-TB
and the DF12 mating connector are not in the library.

## What two sets cost at JLCPCB

The assembly figures here are an estimate built from JLCPCB's published fee tables and the prices above. The
bare boards have a real figure from their quote tool, in the next section.

For the two motor driver boards, assembled on both sides (the board has 44 parts on top and 25 underneath, which
puts it on their Standard service):

| Item | USD |
|---|---|
| Parts, 2 boards x 51.00 (38 of 41 lines) | 102 |
| Setup, double-sided Standard assembly | 50 |
| Stencil | from 1.50 |
| Loading fee, 41 different parts at 1.50 to 3.00 each | 62 to 123 |
| Solder joints, 286 pads x 2 boards x 0.0016 | 1 |
| Total before the bare boards, shipping and import tax | about 216 to 279 |

Not in that total: fabricating the boards themselves (minimum order 5 of each), the two IR encoder boards per
robot (7 parts each, easier to solder by hand than to pay a second USD 50 setup), the encoder discs, flex cables,
base station and programming shield, motors, magnets and battery.

## What JLCPCB's quote tool says for the bare boards

Read from https://cart.jlcpcb.com/quote on 16 November 2026, not signed in, 5 boards of each (their minimum),
standard build time, default colour and finish. The motor driver Gerbers exported from the KiCad board were
uploaded; the tool read them as "4 layer board of 22.18 x 23.17 mm" (`jlcpcb_quote_motor_driver.png`). The
other boards were priced by entering their size.

| Board | As quoted | USD for 5 |
|---|---|---|
| `motor_driver_v3` | 4 layers, 0.8 mm thick, 0.3 mm smallest via hole (their default) | 8.10 |
| `motor_driver_v3` | 4 layers, 0.8 mm thick, 0.2 mm via hole, which is what the board is drawn with | 44.61 |
| `ir_encoder_v2` | 2 layers, 1.6 mm thick | 4.20 |
| `ir_encoder_v2` | 2 layers, 0.4 mm thick as drawn | 33.30 |
| `encoder_wheel` | 2 layers, 1.6 mm thick | 4.20 |
| `master_board` | 2 layers, 1.6 mm thick | 4.00 |
| `programming_shield` | 2 layers, 1.6 mm thick | 4.10 |

The 0.2 mm via price is 8.00 base, 3.32 material, 16.61 for the small vias, 16.58 for the electrical test they
then require and 0.10 edge finishing. For 4 layers the tool greys out 0.4 mm and 0.6 mm, so 0.8 mm is the
thinnest it will make; the authors' board is 0.57 mm. Shipping showed as USD 26.08 by UPS for one board type,
to the tool's default destination, which was not set to the UK. The flex cable is a different product (flexible
PCB) and was not quoted. The assembly price above is still the fee-table estimate: their assembly quote needs
a signed-in account.

Putting the two together for 2 working motor driver boards: about 216 to 279 for parts and assembly plus 44.61
for boards as drawn, so roughly USD 260 to 325 before shipping and import tax, and only if the four parts at
zero stock are found elsewhere.

Two things stop this being ordered as drawn. The motor driver is a 4-layer board 0.57 mm thick, and the 4-layer
thicknesses JLCPCB lists start at 0.8 mm (the authors' note says they used PCBCart for 0.5 mm). And the radio,
motor driver chip and both Hirose connectors are at zero stock, so they would have to be bought elsewhere and
sent in, or the board changed. Both are reasons the redesign should start from a current radio module instead of
rebuilding this board.

Fee sources: https://jlcpcb.com/help/article/pcb-assembly-price , https://jlcpcb.com/solutions/pcb-prototype-assembly ,
https://jlcpcb.com/capabilities/PCB-capabilities
