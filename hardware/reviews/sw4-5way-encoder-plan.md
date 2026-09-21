# SW4: swap the obsolete nav switch for a real 5-way encoder

2026-09-09. Everything here is verified and ready to apply. **One thing is
missing and it is the only reason this is not already in the design: a KiCad
footprint.** See "The one blocker" at the bottom.

---

## The part

**Alps Alpine RKJXT1F42001** — 4-direction stick, centre push, AND a rotary
encoder in a single through-hole part. This is literally the "5-way
encoder/controller" originally asked for, and it replaces the discontinued
SKQUCAA010.

| | |
|---|---|
| Body | 17.0 x 17.0 x 10.5 mm |
| Encoder | 30 detents / 15 pulses per revolution |
| Centre push | 0.3 +/- 0.2 mm travel |
| Stick throw | 9 degrees max per direction |
| Rating | 5 V DC, 10 mA |
| Life | 50,000 cycles |
| Terminals | 10, ø1.0 mm, plus a ø1.1 mm locating hole |
| Mouser | $9.05 qty1, $8.60 qty10, **1,280 in stock, Active** |
| LCSC | C160841, $5.21 qty1, $4.52 qty10, **4,831 in stock** |

## Pinout (verified via the EasyEDA library for C160841)

| Terminal | Function |
|---|---|
| A, B, C, D | the four direction contacts |
| 5 | centre PUSH |
| 6 | COM (common for directions + push) |
| 7 | E_B, encoder phase B |
| 8 | E_A, encoder phase A |
| 9 | E_C, encoder common |
| 10 | unnamed in the library, most likely a frame/shell terminal |

## Teensy pin budget: confirmed, there is room

Currently used: 2-25, 28-40. **Free: 0, 1, 26, 27, 41.**

The encoder needs two more pins beyond the old SKQUCAA010's six. Allocate:

- **pin 26 -> NAV_ENC_A**
- **pin 27 -> NAV_ENC_B**

That still leaves 0, 1 and 41 spare. Pins 26 and 27 are plain GPIO with no
peripheral conflict, which is what a quadrature encoder wants.

## Net mapping to apply

```
A  -> NAV_UP        (direction-to-pin mapping is firmware-remappable)
B  -> NAV_DOWN
C  -> NAV_LEFT
D  -> NAV_RIGHT
5  -> NAV_PUSH
6  -> GND
7  -> NAV_ENC_B     (Teensy 27)
8  -> NAV_ENC_A     (Teensy 26)
9  -> GND
10 -> no-connect    (do NOT tie to GND until the datasheet confirms what it is)
```

Keep the existing active-low convention: 10k pull-up to +3V3_D and a 100nF
debounce cap on each of the six switch lines, and add the same on NAV_ENC_A and
NAV_ENC_B (the encoder contacts are mechanical and bounce like any switch).
That is two more resistors and two more capacitors.

## What this changes downstream

1. **SW3 keeps its job.** SW3 stays the master gain encoder; SW4 becomes nav
   plus a menu scroll wheel. Two encoders is the point, not a mistake.
2. **Bigger part.** 17 x 17 mm against the old 11.2 x 13 mm at (91, 73.5), so
   the control row needs a placement check before routing.
3. **Full re-route** once placement settles.
4. **Height.** The body is 10.5 mm and the lid underside is 15.5 mm above the
   board, so it needs a knob roughly 9-11 mm tall. Alps designs this family
   expecting a customer-supplied knob, which is how it works in car head units.
   3D printing one is fine for a prototype.
5. **Firmware.** Add a quadrature decoder on pins 26/27 for menu scroll.

## The one blocker: no KiCad footprint exists

I could not obtain a verified land pattern from any available source:

- Alps product page: outline specs only (17 x 17 x 10.5)
- Alps PDF catalogue: gives "10-ø1 hole", "ø1.1 hole" and "For position lug
  15.6", but not the pad coordinate grid
- Alps Reference Drawing: behind an inquiry form
- Alps 3D CAD: a .zip, not readable here
- SnapEDA/SnapMagic: blocks automated access
- SamacSys ComponentSearchEngine: no model for this MPN
- EasyEDA API: robots-disallowed

**I deliberately did not invent the pad positions.** A wrong 10-pin
through-hole footprint produces a board that cannot be assembled, which is a
worse outcome than the obsolete part it replaces.

### Fastest way to unblock (about two minutes)

Open LCSC part **C160841** in EasyEDA and export the footprint, then drop it
into `hardware/QuadPreRecorder.pretty/`. EasyEDA definitely has one:
`has_easyeda_footprint: true`, footprint UUID
`f2c3764afb3c4f93a8c5faf618ae8163`.

Alternatives: request the Reference Drawing from Alps at
`tech.alpsalpine.com/e/inquiry/catalog/?category=reference-drawing&product=MU&partnumber=RKJXT1F42001`,
or buy one and measure it.

Once that footprint exists, everything above is mechanical to apply and the
board can be re-routed.
