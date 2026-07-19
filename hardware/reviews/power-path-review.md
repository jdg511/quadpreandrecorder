# Power-path review

## Path inventory

| Path | Source | Protection/conversion | Loads | Result |
|---|---|---|---|---|
| +9V | J1 center-positive barrel | 750 mA resettable fuse, SS14 series polarity diode, SMBJ12A TVS, 100 uF + ceramic bulk | Electret bias, CD4053, OPA1654, TLE2426, 5 V buck | Connected and protected for regulated 9 V input |
| +5V | TPS62160 buck | 2.2 uH, 2x22 uF, feedback/feed-forward, PG pull-up | Teensy VIN through SS14, TFT header/backlight, LDO, TPA6132A2 | About 4.98 V nominal; rail has local bulk/decoupling |
| +3V3_A | TPS7A2033 LDO | 1 uF input, 4.7 uF output | PCM1864 analog, PCM5102 analog | Separate low-noise analog rail |
| +3V3_D | Teensy 3.3 V output pins | Local 10 uF/100 nF at codecs | PCM1864 digital/IO, PCM5102 digital, logic pull-ups | Current budget must be confirmed during bring-up |
| VREF | TLE2426 | NR capacitor, 47 uF + 100 nF output | Four preamps and pad dividers | 4.5 V audio midpoint; not tied to digital midpoint |
| CHASSIS | DE-9 pin 5/shell | 1 MOhm parallel 1 nF; optional 0 Ohm DNP | Cable jacket and metal enclosure | Circuit/shield coupling is controlled at entry |

## Sequencing and fault behavior

- The 9 V rail is present before the 5 V, 3.3 V analog, and Teensy-generated
  digital rails. ADC/DAC control pins have series damping or pull resistors and
  firmware must keep DAC mute/headphone enable inactive during startup.
- The Teensy VIN path is diode-isolated from +5 V, but USB VBUS can still create
  a second supply path inside the module. Cut its VIN/VUSB trace before using
  USB and barrel power simultaneously.
- A short on a capsule bias line is limited mainly by its 4.7 kOhm resistor.
- TVS D2 clamps after the polarity diode. F1 limits sustained input faults; it
  is not a precision current limiter.

## Layout review

- Power entry/buck parts are grouped away from J2 and the four input channels.
- The switching node is localized around U1/L1. Analog input RC parts are at U7.
- Both copper layers have filled GND pours; the bottom pour is the primary
  return plane. No split ground crosses audio or serial-clock routes.
- DRC confirms 0 shorts, 0 clearance violations, and 0 unconnected pads.

Status: suitable for a Rev A prototype. Rail noise, thermal rise, startup mute,
and Teensy 3.3 V current margin require bench measurements before production.
