"""
Anthem x40 percent/dB volume scale conversion.

The x40 series exposes two volume controls: ZzVOL in dB and ZzPVOL as a
percentage. The percentage is not a linear mapping of the dB range - it is a
taper, coarse at the bottom and fine at the top. From the "Terse volume mapping
table" in knowledge-base/MRX-x40-AVM-70-90-IP-RS-232-v5.xls:

    [0% = -90 dB] step 4 dB [4% = -74 dB] step 3 dB [11% = -53 dB]
    step 2 dB [20% = -35 dB] step 1 dB [30% = -25 dB] step 0.5 dB [100% = +10 dB]
    Converted dB round up to the next per cent.

The receiver's Maximum Volume setting (GCMMV) does not rescale this table.
Verified on an MRX 540 with GCMMV-20.0: Z1PVOL20 still reported Z1VOL-35.0,
the unscaled table value. The ceiling clamps instead - Z1PVOL45 was answered
with "Z1VOL-20.0;Z1PVOL40;", the receiver pinning the request at the ceiling
and echoing back the clamped percentage. Every percentage above that ceiling
is dead travel on a UI slider, which is what max_percent() exists to trim.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from math import ceil

# (percent, dB) breakpoints of the taper. Linear between adjacent pairs.
_TABLE: tuple[tuple[int, float], ...] = (
    (0, -90.0),
    (4, -74.0),
    (11, -53.0),
    (20, -35.0),
    (30, -25.0),
    (100, 10.0),
)

DB_MIN = _TABLE[0][1]
DB_MAX = _TABLE[-1][1]

# Options.VOLUME_STEPS only accepts 2-100.
_MIN_STEPS = 2


def percent_to_db(percent: int) -> float:
    """Convert a receiver percentage (ZzPVOL) to dB."""
    pct = max(0, min(100, percent))
    for (p0, d0), (p1, d1) in zip(_TABLE, _TABLE[1:]):
        if pct <= p1:
            return d0 + (pct - p0) * (d1 - d0) / (p1 - p0)
    return DB_MAX


def db_to_percent(db: float) -> int:
    """Convert dB (ZzVOL) to the receiver percentage, rounding up per the spec."""
    value = max(DB_MIN, min(DB_MAX, db))
    for (p0, d0), (p1, d1) in zip(_TABLE, _TABLE[1:]):
        if value <= d1:
            return ceil(p0 + (value - d0) * (p1 - p0) / (d1 - d0))
    return 100


def db_to_percent_exact(db: float) -> float:
    """Continuous inverse of the taper, without the spec's round-up.

    db_to_percent() rounds up to a whole receiver percent because that is what
    ZzPVOL accepts. For *display* that quantisation throws away resolution: in
    the -53..-35 dB band one percent spans 2 dB, so a 0.5 dB VDN step moves the
    integer percent only every fourth press. The receiver pushes ZzVOL on every
    press, so the UI is driven from dB through this continuous form instead.
    """
    value = max(DB_MIN, min(DB_MAX, db))
    for (p0, d0), (p1, d1) in zip(_TABLE, _TABLE[1:]):
        if value <= d1:
            return p0 + (value - d0) * (p1 - p0) / (d1 - d0)
    return 100.0


def max_percent(max_db: float | None) -> int:
    """Receiver percentage corresponding to the Maximum Volume (GCMMV) ceiling.

    Returns 100 when no ceiling is known, so an unconfigured or non-x40 device
    behaves exactly as it did before this scaling existed.
    """
    if max_db is None:
        return 100
    return max(_MIN_STEPS, db_to_percent(max_db))


def to_ui(device_percent: float, max_pct: int) -> int:
    """Map a receiver percentage onto the 0-100 the UC slider works in."""
    if max_pct >= 100:
        return max(0, min(100, device_percent))
    return max(0, min(100, round(device_percent * 100 / max_pct)))


def to_device(ui_percent: float, max_pct: int) -> int:
    """Map the UC slider's 0-100 back onto a reachable receiver percentage."""
    if max_pct >= 100:
        return max(0, min(100, round(ui_percent)))
    return max(0, min(max_pct, round(ui_percent * max_pct / 100)))
