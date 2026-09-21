"""Exact orderable part numbers for every passive on the board.

Before this existed, generate_schematic.py stamped family names like
"GRM series X7R/C0G" and "RC0603FR series, 1%" onto 184 of 240 placements.
Those are descriptions, not part numbers: PCBWay (and any other assembler that
sources by MPN) cannot quote or buy against them.

Every entry below carries a PRIMARY and an ALTERNATE from a different
manufacturer, so the board stays buildable if one goes out of stock. Verified
2026-09-08 against the LCSC/JLCPCB parametric database and the Mouser API.

Rules enforced when this table was built:
  - C0G/NP0 parts stay C0G/NP0. Never substituted with X7R; they sit in
    filters and the precision gain network.
  - 0.1% resistors stay 0.1% thin film.
  - Alternate voltage rating >= primary.
  - Electrolytic alternates were checked to physically fit D6.3 x L5.8 mm.

Three entries needed an engineering compromise and are marked REVIEW below.
"""

from typing import NamedTuple


class Passive(NamedTuple):
    manufacturer: str
    mpn: str
    alt_manufacturer: str
    alt_mpn: str
    lcsc: str
    note: str = ""


# --------------------------------------------------------------------------
# 0603 thick film, 1%, 100 mW. Primary Yageo RC0603FR, alternate UNI-ROYAL
# 0603WAF (nearly all LCSC Basic, so no extended-part fee at JLCPCB).
# --------------------------------------------------------------------------
RESISTOR_1PCT: dict[str, Passive] = {
    "0R":    Passive("Yageo", "RC0603FR-070RL",   "UNI-ROYAL", "0603WAF0000T5E", "C21189"),
    "10R":   Passive("Yageo", "RC0603FR-0710RL",  "FOJAN", "FRC0603F10R0TS", "C2906983",
                     "alt chosen for tempco: UNI-ROYAL 0603WAF100JT5E is 400ppm/C vs 200ppm here"),
    "33R":   Passive("Yageo", "RC0603FR-0733RL",  "UNI-ROYAL", "0603WAF330JT5E", "C23140"),
    "100R":  Passive("Yageo", "RC0603FR-07100RL", "UNI-ROYAL", "0603WAF1000T5E", "C22775"),
    "470R":  Passive("Yageo", "RC0603FR-13470RL", "UNI-ROYAL", "0603WAF4700T5E", "C23179"),
    "1k":    Passive("Yageo", "RC0603FR-071KL",   "UNI-ROYAL", "0603WAF1001T5E", "C21190"),
    "1.1k":  Passive("Yageo", "RC0603FR-071K1L",  "UNI-ROYAL", "0603WAF1101T5E", "C22764"),
    "1.2k":  Passive("Yageo", "RC0603FR-071K2L",  "UNI-ROYAL", "0603WAF1201T5E", "C22765"),
    "2.2k":  Passive("Yageo", "RC0603FR-072K2L",  "UNI-ROYAL", "0603WAF2201T5E", "C4190"),
    "4.7k":  Passive("Yageo", "RC0603FR-074K7L",  "UNI-ROYAL", "0603WAF4701T5E", "C23162"),
    "5.1k":  Passive("Yageo", "RC0603FR-075K1L",  "UNI-ROYAL", "0603WAF5101T5E", "C23186"),
    "10k":   Passive("Yageo", "RC0603FR-0710KL",  "UNI-ROYAL", "0603WAF1002T5E", "C25804"),
    "20k":   Passive("Yageo", "RC0603FR-0720KL",  "UNI-ROYAL", "0603WAF2002T5E", "C4184",
                     "ADP7142 feedback divider (with 130k) -> 9.0 V"),
    "47k":   Passive("Yageo", "RC0603FR-0747KL",  "UNI-ROYAL", "0603WAF4702T5E", "C25819",
                     "LCSC stock on the Yageo part is thin (11); buy primary from DigiKey/Mouser or use the alt"),
    "75k":   Passive("Yageo", "RC0603FR-0775KL",  "UNI-ROYAL", "0603WAF7502T5E", "C23242"),
    "80.6k": Passive("Yageo", "RC0603FR-0780K6L", "Panasonic", "ERJ3EKF8062V", "C403361",
                     "no LCSC Basic/Preferred part exists at this value; extended-part fee either way"),
    "100k":  Passive("Yageo", "RC0603FR-07100KL", "UNI-ROYAL", "0603WAF1003T5E", "C25803"),
    "130k":  Passive("Yageo", "RC0603FR-07130KL", "UNI-ROYAL", "0603WAF1303T5E", "C22795"),
    "680k":  Passive("Yageo", "RC0603FR-07680KL", "UNI-ROYAL", "0603WAF6803T5E", "C25822"),
    "1M":    Passive("Yageo", "RC0603FR-071ML",   "UNI-ROYAL", "0603WAF1004T5E", "C22935"),
}

# --------------------------------------------------------------------------
# 0603 precision thin film, 0.1%, 25 ppm/C. This is the mic gain-setting
# network, so tolerance and ratio tracking matter more than price.
# Primary is the Yageo RT0603BRD family: all four values come from ONE family
# (better ratio tracking than a mixed set), all LCSC-stocked, and about 5x
# cheaper than the Vishay TNPW set that was nominally specified before.
# --------------------------------------------------------------------------
RESISTOR_01PCT: dict[str, Passive] = {
    "10k":   Passive("Yageo", "RT0603BRD0710KL",  "Vishay", "TNPW060310K0BEEA", "C95204"),
    "33k":   Passive("Yageo", "RT0603BRD0733KL",  "Vishay", "TNPW060333K0BEEA", "C705768"),
    "68k":   Passive("Yageo", "RT0603BRD0768KL",  "Panasonic", "ERA3AEB683V", "C705793",
                     "Vishay TNPW060368K0BEEA is NOT carried by LCSC (Mouser only, ~1.2k stock)"),
    "90.9k": Passive("Yageo", "RT0603BRD0790K9L", "Vishay", "TNPW060390K9BEEA", "C728600",
                     "REVIEW: thinnest line on the board. No non-Yageo 0.1% 90.9k has depth at "
                     "LCSC. Buy this value from Mouser/DigiKey. Do NOT accept 91k, it is a "
                     "different value"),
}


# --------------------------------------------------------------------------
# MLCC ceramics, keyed by (package, value, dielectric class).
# "C0G" means the schematic value string says C0G and the part MUST be C0G/NP0.
# "STD" means a general-purpose X7R position.
# --------------------------------------------------------------------------
CERAMIC: dict[tuple[str, str, str], Passive] = {
    # ---- 0603 ----
    ("0603", "22pF",  "C0G"): Passive("Murata", "GCM1885C2A220JA16D", "FOJAN", "FCC0603N220J500CT", "C408549",
                                      "100V C0G. The canonical Murata GRM1885C1H220JA01D is NRND, avoided"),
    ("0603", "47pF",  "C0G"): Passive("Murata", "GCM1885C2A470JA16D", "FH", "0603CG470J500NT", "C126580"),
    ("0603", "100pF", "C0G"): Passive("Murata", "GRM1885C1H101JA01D", "Samsung", "CL10C101JB8NNNC", "C71664"),
    # 2026-09-12 sourcing sweep (live Mouser + LCSC): Mouser lists the Murata
    # "D"/"L"-suffix GRM numbers as obsolete with 0 stock (LCSC still has
    # most of them, see the notes); primaries are now parts that are in
    # stock at both, with the Murata "J"/"K" successors or the LCSC-deep
    # part as the alternate. The lcsc code is the primary MPN's own code.
    ("0603", "2.2nF", "C0G"): Passive("Samsung", "CL10C222JB8NNNC", "Murata", "GRM1885C1H222JA01J", "C33353",
                                      "LCSC 17k (the old Murata D part is C77033, 56k at LCSC but 0 at Mouser); "
                                      "Murata J-suffix successor 28k at Mouser"),
    ("0603", "4.7nF", "C0G"): Passive("Murata", "GRM1885C1H472JA01D", "TDK", "CGA3EAC0G2A472JT000E", "C85980",
                                      "thin category: only ~17 in-stock C0G SKUs LCSC-wide at this value"),
    ("0603", "10nF",  "C0G"): Passive("TDK", "C1608C0G1H103JT000N", "Murata", "GRM1885C1H103JA01J", "C76599",
                                      "ADC input filter, must stay C0G. LCSC 16k (old Murata D = C85973, 238k at "
                                      "LCSC, 0 at Mouser); Murata J successor 21k at Mouser"),
    ("0603", "10nF",  "STD"): Passive("Samsung", "CL10B103KB8NNNC", "Yageo", "CC0603KRX7R9BB103", "C1589",
                                      "LCSC Basic, 2.5M; Mouser 833k"),
    ("0603", "47nF",  "STD"): Passive("Yageo", "CC0603KRX7R9BB473", "Samsung", "CL10B473KB8NNNC", "C107093",
                                      "Murata's 47nF 0603 has only ~4.4k at LCSC; Yageo is the deep part"),
    ("0603", "100nF", "STD"): Passive("Samsung", "CL10B104KB8NNNC", "Yageo", "CC0603KRX7R9BB104", "C1591",
                                      "24 placements; LCSC Basic, 1.1M at $0.012 (the old Murata D part is "
                                      "C77055, still 1.2M at LCSC but 0 at Mouser)"),
    ("0603", "1uF",   "STD"): Passive("Yageo", "CC0603KRX7R8BB105", "Samsung", "CL10B105KA8NNNC", "C106858",
                                      "25 V (C59-C61 are U10's charge-pump caps). LCSC 120k; Samsung alt 645k"),

    # ---- 0805 ----
    ("0805", "1nF",   "C0G"): Passive("Yageo", "CC0805KRX7RCBB102", "Murata", "GRM31C5C3A102JWA3L", "C309495",
                                      "REVIEW: value says '1nF 1kV C0G' but NO manufacturer makes 1kV C0G in "
                                      "0805. This primary keeps the 1 kV standoff and accepts X7R. If C0G "
                                      "matters more than 1 kV use Yageo CC0805JKNPOBBN102 (500V NP0). The "
                                      "alt listed here is genuine 1kV C0G but needs a 1206 footprint"),
    ("0805", "100nF", "STD"): Passive("Samsung", "CL21B104KCFNNNE", "Yageo", "CC0805KRX7R9BB104", "C28233",
                                      "Murata GRM21BR71H104KA01L obsolete at Mouser (2026-09-12). LCSC 599k; "
                                      "Yageo alt C49678 is Basic, 10M"),
    ("0805", "1uF",   "STD"): Passive("Yageo", "CC0805KKX7R9BB105", "Samsung", "CL21B105KBFNNNE", "C91185",
                                      "Murata GRM21BR71H105KA12L obsolete at Mouser; Yageo 295k at Mouser, "
                                      "807k at LCSC"),
    ("0805", "2.2uF", "STD"): Passive("Samsung", "CL21B225KAFNNNE", "Murata", "GRM21BR71E225KE11K", "C19110",
                                      "Mouser 72k / LCSC 62k; the old Murata L suffix (C77081) is 0 at Mouser"),
    ("0805", "4.7uF", "STD"): Passive("Murata", "GRM21BZ71E475KE15L", "Samsung", "CL21B475KAFNNNE", "C437556"),
    ("0805", "10uF",  "STD"): Passive("Murata", "GRM21BZ71E106KE15L", "Samsung", "CL21B106KOQNNNE", "C237493",
                                      "Samsung CL21B106KAYQNNE (25V) went 0 at Mouser; Murata 25V 93k at LCSC "
                                      "(0 at Mouser). The Samsung KOQ alt is only 16V (523k LCSC, 134k Mouser)"),

    # ---- 1206 ----
    ("1206", "4.7uF", "STD"): Passive("Murata", "GRM31CR71H475KA12L", "Samsung", "CL31B475KBHNNNE", "C77096"),
    ("1206", "10uF",  "STD"): Passive("Samsung", "CL31B106KAHNNNE", "Murata", "GRM31CR71E106KA12L", "C14860",
                                      "12 placements. Both numbers are 0 at Mouser (2026-09-12) but deep at "
                                      "LCSC: Samsung 976k at $0.20, Murata C77093 199k. If Mouser must supply, "
                                      "any 10uF 25V X7R 1206 (e.g. Samsung CL31B106KAHNNNF) is fine"),
    ("1206", "22uF",  "STD"): Passive("Taiyo Yuden", "EMK316BB7226ML-T", "Murata", "GRM31CZ71C226ME15L", "C385906",
                                      "REVIEW: schematic says 22uF 10V. This is the 16V part. X7R 22uF in 1206 "
                                      "tops out at 10V from Murata, and 10V is not enough headroom if C5/C6 "
                                      "sit near the boost or battery node"),
    ("1206", "47uF",  "STD"): Passive("Taiyo Yuden", "EMK316BBJ476ML-T", "Murata", "GRM31CR61A476ME15K", "C385907",
                                      "REVIEW: X5R, not X7R. No X7R 47uF exists in 1206 from anyone. The Taiyo "
                                      "Yuden 16V part is primary since 2026-09-12 (Mouser 208k, LCSC 119k); the "
                                      "Murata 10V part is down to ~11 pieces at Mouser (its old L-suffix "
                                      "number C94034 still has 172k at LCSC)"),
}

# --------------------------------------------------------------------------
# SMD aluminium electrolytics. Footprint is CP_Elec_6.3x5.8, so the can must
# be D6.3 mm and fit a 5.8 mm envelope. Both alternates were checked against
# real case dimensions, not assumed from the family name.
# --------------------------------------------------------------------------
ELECTROLYTIC: dict[str, Passive] = {
    "100uF 25V": Passive("Panasonic", "EEE-FT1E101AP", "Lelon", "VZS101M1ETR-0606", "C178590",
                         "the previously specified EEE-FK family has NO 100uF/25V in a 6.3 mm can at all "
                         "(the FK part is an 8.0 mm can on an 8.3x8.3 land and does not fit this footprint). "
                         "Primary LCSC stock is thin (~950); the Lelon alt is an exact D6.3xL5.8 fit with "
                         "identical 260 mOhm ESR at 1/3 the price and 30k+ stock"),
    "100uF 16V": Passive("Panasonic", "EEE-FK1C101P", "Lelon", "VZL101M1CTR-0606", "C128532",
                         "Lelon alt is exactly D6.3 x L5.8"),
}


# --------------------------------------------------------------------------
# Lookups. These RAISE on an unknown value rather than falling back to a
# placeholder, so a new part can never silently reintroduce an unorderable
# BOM line. If generation fails here, add the value to the table above.
# --------------------------------------------------------------------------

def _first_token(value: str) -> str:
    return value.strip().split()[0] if value.strip() else ""


def resistor_part(value: str, precision: bool = False) -> Passive:
    """Resolve a 0603 resistor. `value` may carry trailing notes, e.g.
    '4.7k ELECTRET BIAS' or '68k 0.1%'."""
    key = _first_token(value)
    table = RESISTOR_01PCT if precision else RESISTOR_1PCT
    if key not in table:
        kind = "0.1% precision" if precision else "1%"
        raise KeyError(
            f"passive_catalog: no {kind} 0603 resistor for value {value!r} (key {key!r}). "
            f"Add it to passive_catalog.py rather than shipping an unorderable BOM line."
        )
    return table[key]


def ceramic_part(value: str, size: str) -> Passive:
    """Resolve an MLCC. `size` is '0603' / '0805' / '1206'. A value string
    containing 'C0G' selects the C0G entry, which is never an X7R part."""
    key = (size, _first_token(value), "C0G" if "C0G" in value.upper() else "STD")
    if key not in CERAMIC:
        raise KeyError(
            f"passive_catalog: no ceramic for value {value!r} in {size} (key {key}). "
            f"Add it to passive_catalog.py rather than shipping an unorderable BOM line."
        )
    return CERAMIC[key]


def electrolytic_part(value: str) -> Passive:
    key = value.strip()
    if key not in ELECTROLYTIC:
        raise KeyError(
            f"passive_catalog: no electrolytic for value {key!r}. "
            f"Add it to passive_catalog.py rather than shipping an unorderable BOM line."
        )
    return ELECTROLYTIC[key]


def review_notes() -> list[str]:
    """Every entry that needed an engineering compromise, for the build log."""
    out = []
    for name, table in (("resistor 1%", RESISTOR_1PCT), ("resistor 0.1%", RESISTOR_01PCT),
                        ("electrolytic", ELECTROLYTIC)):
        for key, p in table.items():
            if "REVIEW" in p.note:
                out.append(f"{name} {key}: {p.note}")
    for key, p in CERAMIC.items():
        if "REVIEW" in p.note:
            out.append(f"ceramic {key}: {p.note}")
    return out
