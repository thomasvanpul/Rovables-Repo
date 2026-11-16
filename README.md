# Rovables, forked

This is a fork of [adementyev/Rovables-Repo](https://github.com/adementyev/Rovables-Repo), the design files for
Rovables, the miniature on-body robots by Artem Dementyev, Hsin-Liu (Cindy) Kao, Inrak Choi, Deborah Ajilo,
Maggie Xu, Sean Follmer, Joe Paradiso and Chris Schmandt, with the undergraduate students they name below
(MIT Media Lab and Stanford Shape Lab, UIST 2016).
Their work is MIT licensed (`LICENSE.md`) and is kept here unchanged. Their README follows below, as they wrote it.

## What this fork adds

Everything the original authors made is where they left it. Additions are in new folders only:

| Folder | What | State |
|---|---|---|
| `mechanical/converted/` | Their SolidWorks parts as STEP and STL, so they open without SolidWorks | 11 of 11 custom parts converted |
| `printables/` | The parts oriented and plated for an FDM printer (Bambu P1S, PLA), with the script that builds them | sliced, not yet printed |
| `electronics/kicad/` | Their six Altium boards imported into KiCad 10 | boards import and open; four schematics converted, 139 of 141 nets identical to the boards |
| `electronics/bom/` | One parts list with stock and price per line, and what two sets cost | checked 16 Nov 2026 |

## v2 (Imperial, 2026)

Everything above this heading describes the original design and faithful conversions of it. This section is
different: `v2/` is a new robot that borrows the original's idea and none of its parts.

| | Whose work | Where |
|---|---|---|
| The Rovables design: boards, CAD, firmware, paper | The original authors, unchanged | `electronics/`, `mechanical/`, `software/`, `images/` |
| Conversions of their files, print plates, parts list | This fork, from their geometry and netlists | `mechanical/converted/`, `printables/`, `electronics/kicad/`, `electronics/bom/` |
| Rovable v2 | This fork, new | `v2/` |

v2 is about twice the size, runs on two N20 gear motors with 8.92 x 25 mm rod magnets as its wheels, and swaps
the radio, processor and USB base station for one ESP32 that a Mac talks to over Bluetooth. Its body is written
as code and prints in PLA without supports.

![Rovable v2 in Fusion](v2/cad/out/fusion_iso.png)

State on 16 Nov 2026: modelled, sliced (one plate, 1 h 14 min), firmware compiles for ESP32-C3 and ESP32-S3.
Not printed, not wired, not driven. [`v2/README.md`](v2/README.md) has the design, the print and build steps,
and the list of what is still assumed; [`v2/evidence/README.md`](v2/evidence/README.md) has the bench test it
starts from.

Fork maintained by Thomas van Pul. Additions are under the same MIT licence.

---

# Rovables Project 

## Introduction
This repository has all the design files to assemble the robots. Rovables are miniature wearable robots that can move around the body. 
See the paper we published at UIST conference [here](http://www.artemdementyev.com/wp-content/uploads/2016/10/Rovables-Miniature-On-Body-Robots-as-Mobile-Wearables.pdf).  

![Rovables rendered](/images/rovables-render.jpg)
![Shirt pic](/images/rovables-main.jpg)

## Content
electronics/ - contains the circuit boards design. They were all designed using Altium, so it might be required to see the original files

mechanical/ - This folder contains mechanical files, done in SolidWorks 2016. 

software/ - contains the software that runs on the devices. We used the Arduino platform, so the robots can be easily programmed.  


## Manufacturing and design
The design contains many 3D printed custom parts and custom circuit boards. Making the design will require at least a good resolution 3D printer (Formlabs or Eden260). Other printers might work also, but we haven't tried them. 

## Known Issues
The same nRF42 library is used for the robot and the receiver. Change in nRF52.cpp file: #define TEENSY_MASTER_BOARD depending on which one, since they use different SPI port definitions. 

The localization of the robot is not implemented in the current code. This version has high resolution wheel encoders and a powerful ARM processor, so the tracking will be better. 

## Aknowledgements
This project was a collaboration between MIT Media Lab (Responsive Environments and Living Mobile) and Shape Lab at Stanford University

The poeple who worked on this project are:

Graduate students: Artem Dementyev, Hsin-Liu (Cindy) Kao, Inrak Choi, Deborah Ajilo, Maggie Xu. 

The faculty: Sean Follmer, Joe Paradiso, Chris Schmandt.

Undegraduate students: Lucas Santana, Karla-Sofia Zapata-Garcia, Cheyenne Hua, and Diana Lamaute

![Shapelab Logo](/images/shapelab.png)
![MediaLab Logo](/images/medialablogo.png)
