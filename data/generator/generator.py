"""
ICARUS Dataset Generator
Creates the 3 student files + the private answer key.
Run once. Do not re-run unless you want to regenerate everything.
"""

import csv
import json
import random
import os
from datetime import datetime, timedelta

# Fix randomness so results are reproducible
random.seed(42)

# ---------- Output folder ----------
OUT = os.path.join(os.path.dirname(__file__), "..", "dataset")
os.makedirs(OUT, exist_ok=True)

# ---------- Flight parameters ----------
TOTAL_SECONDS = 3600          # 1 hour flight
SAMPLE_EVERY = 1              # 1 reading per second -> 3600 rows
LAUNCH_LAT = 12.9716
LAUNCH_LON = 77.5946

# Anomaly times (in seconds from start)
T_GPS_JUMP       = 1240
T_BATTERY_DROP   = 2100
T_ALT_STUCK_START = 2700
T_ALT_STUCK_END   = 2850
T_TEMP_DECOY     = 600
T_TEMP_OFFSET_START = 1800
T_BAD_LAT_ROW    = 1900

# ---------- Helper: realistic flight profile ----------
def altitude_at(t):
    """Smooth up-and-down arc. Peaks around t=1500s."""
    if t < 300:
        return 0
    peak_time = 1500
    peak_alt = 1000
    if t <= peak_time:
        # ascent
        return round(peak_alt * ((t - 300) / (peak_time - 300)) ** 1.5, 2)
    else:
        # descent
        frac = (t - peak_time) / (TOTAL_SECONDS - peak_time)
        return round(peak_alt * max(0, 1 - frac ** 0.7), 2)

def battery_at(t):
    """Slow linear decay from 4.20V to 3.60V."""
    return round(4.20 - (0.60 * t / TOTAL_SECONDS), 3)

def temp_at(t):
    """Nominal: starts at 28C, cools to 15C by end."""
    return round(28 - (13 * t / TOTAL_SECONDS), 2)

def lat_at(t):
    return round(LAUNCH_LAT + (t * 0.00002), 6)

def lon_at(t):
    return round(LAUNCH_LON + (t * 0.00003), 6)

def timestamp_for(t):
    """Return a timestamp string. Deliberately mix 3 formats."""
    base = datetime(2026, 9, 25, 10, 0, 0)
    dt = base + timedelta(seconds=t)
    if t < 1200:
        # Format 1: Unix epoch
        return str(int(dt.timestamp()))
    elif t < 2400:
        # Format 2: ISO8601 with timezone
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # Format 3: seconds since boot
        return f"{t}s"

# ---------- Build telemetry rows ----------
rows = []
for t in range(0, TOTAL_SECONDS, SAMPLE_EVERY):
    alt = altitude_at(t)
    lat = lat_at(t)
    lon = lon_at(t)
    temp = temp_at(t)
    bat = battery_at(t)
    status = 0

    # Inject: GPS jump
    if t == T_GPS_JUMP:
        lat += 0.05
        lon += 0.05
        status = status | (1 << 0)

    # Inject: Battery drop
    if t == T_BATTERY_DROP:
        bat = bat - 0.35
        status = status | (1 << 3)

    # Inject: Altitude stuck
    if T_ALT_STUCK_START <= t <= T_ALT_STUCK_END:
        alt = altitude_at(T_ALT_STUCK_START)

    # Inject: Temperature decoy spike
    if t == T_TEMP_DECOY:
        temp += 3.5

    # Inject: Temperature offset (from calibration issue)
    if t >= T_TEMP_OFFSET_START:
        temp += 4.0

    # Inject: Bad lat row
    if t == T_BAD_LAT_ROW:
        lat = 999

    # Small random noise
    alt += random.uniform(-0.5, 0.5)
    temp += random.uniform(-0.3, 0.3)
    bat += random.uniform(-0.005, 0.005)

    rows.append({
        "packet_id": t + 1,
        "timestamp": timestamp_for(t),
        "altitude_m": round(alt, 2),
        "lat": lat,
        "lon": lon,
        "temp_c": round(temp, 2) if t != 950 else "",  # one missing temp
        "battery_v": round(bat, 3),
        "status_code": status,
    })

# ---------- Inject: Duplicate rows ----------
# Pick ~30 random rows and duplicate them with slightly different values
dupes = random.sample(range(100, len(rows) - 100), 30)
for idx in sorted(dupes, reverse=True):
    dup = rows[idx].copy()
    dup["temp_c"] = round(dup["temp_c"] + 0.1, 2) if dup["temp_c"] != "" else ""
    dup["battery_v"] = round(dup["battery_v"] - 0.001, 3)
    rows.insert(idx + 1, dup)

# Renumber packet ids
for i, r in enumerate(rows):
    r["packet_id"] = i + 1

# ---------- Write telemetry.csv ----------
telemetry_path = os.path.join(OUT, "telemetry.csv")
with open(telemetry_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "packet_id", "timestamp", "altitude_m", "lat", "lon",
        "temp_c", "battery_v", "status_code"
    ])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {telemetry_path} ({len(rows)} rows)")

# ---------- Write commands.log ----------
commands_path = os.path.join(OUT, "commands.log")
commands = [
    ("10:00:00", "CMD_BOOT"),
    ("10:05:00", "CMD_ASCENT_START"),
    ("10:20:40", "CMD_GPS_RESET"),          # t=1240s
    ("10:35:00", "CMD_BATTERY_WARN"),       # t=2100s
    ("10:45:00", "CMD_DESCENT_START"),
    ("10:47:30", "CMD_ALT_SENSOR_FAULT"),   # t=2850s
    ("10:50:00", "CMD_SIGNAL_LOST"),
]
with open(commands_path, "w") as f:
    for ts, cmd in commands:
        f.write(f"[{ts}] {cmd}\n")
print(f"Wrote {commands_path}")

# ---------- Write calibration.json ----------
calib = {
    "temperature": {
        "offset_c": 4.0,
        "applies_after_seconds": T_TEMP_OFFSET_START,
        "note": "Temperature sensor reads 4.0C high after 1800s from boot. Subtract to get true value."
    },
    "altitude": {
        "noise_m": 0.5,
        "note": "Altitude has +/- 0.5m random noise per reading."
    },
    "status_code_bits": {
        "bit_0": "GPS_RESET_FLAG",
        "bit_1": "reserved",
        "bit_2": "reserved",
        "bit_3": "BATTERY_FAULT_FLAG",
        "note": "Bit numbering starts at 0 (least significant)."
    }
}
calib_path = os.path.join(OUT, "calibration.json")
with open(calib_path, "w") as f:
    json.dump(calib, f, indent=2)
print(f"Wrote {calib_path}")

# ---------- Write README.md for students ----------
readme = """# ICARUS Telemetry Dataset

You are analysing the flight of a simulated CanSat called **Icarus**.
The flight lasted approximately one hour. Something went wrong.

## Files

- `telemetry.csv`  - sensor readings (one row per second)
- `commands.log`   - commands sent from the ground station
- `calibration.json` - sensor calibration notes (READ THIS)

## telemetry.csv columns

| Column | Meaning | Units |
|---|---|---|
| packet_id | Sequential ID | - |
| timestamp | Time of reading | mixed formats (see below) |
| altitude_m | Altitude above ground | metres |
| lat / lon | GPS position | decimal degrees |
| temp_c | Temperature | Celsius |
| battery_v | Battery voltage | volts |
| status_code | Bitfield of system flags | integer |

## Timestamp warning

Timestamps are NOT in a single format. You will find:
- Unix epoch (first ~20 minutes)
- ISO8601 with Z suffix (next ~20 minutes)
- Seconds-since-boot with `s` suffix (last ~20 minutes)

You must normalise these before ordering the data.

## status_code

It's a bitfield. See `calibration.json` for bit meanings.

## Your task

1. Parse and clean the data
2. Reconstruct the flight (altitude, GPS path)
3. Find genuine anomalies
4. Explain what happened

**Read `calibration.json` before flagging any temperature or altitude anomaly.**
"""
readme_path = os.path.join(OUT, "README.md")
with open(readme_path, "w") as f:
    f.write(readme)
print(f"Wrote {readme_path}")

# ---------- Write PRIVATE answer key ----------
ground_truth = {
    "flight": {
        "peak_altitude_m": 1000,
        "peak_time_seconds": 1500,
        "total_duration_s": TOTAL_SECONDS
    },
    "real_anomalies": [
        {
            "id": "A1",
            "sensor": "gps",
            "time_seconds": T_GPS_JUMP,
            "description": "Sudden GPS position jump of ~7km, inconsistent with flight.",
            "explained_by": "CMD_GPS_RESET in commands.log at 10:20:40",
            "correct_classification": "real_event"
        },
        {
            "id": "A2",
            "sensor": "battery",
            "time_seconds": T_BATTERY_DROP,
            "description": "Battery voltage drops 0.35V in a single reading, violating decay curve.",
            "explained_by": "status_code bit 3 set at same timestamp; CMD_BATTERY_WARN in log",
            "correct_classification": "sensor_failure"
        },
        {
            "id": "A3",
            "sensor": "altitude",
            "time_seconds": [T_ALT_STUCK_START, T_ALT_STUCK_END],
            "description": "Altitude reads identical value for 150 consecutive seconds while GPS keeps moving.",
            "explained_by": "CMD_ALT_SENSOR_FAULT in commands.log at 10:47:30",
            "correct_classification": "sensor_failure"
        }
    ],
    "decoys": [
        {
            "id": "D1",
            "sensor": "temperature",
            "time_seconds": T_TEMP_DECOY,
            "description": "Single-reading temp spike of +3.5C.",
            "why_not_anomaly": "Within combined noise band (+/-0.3 noise, +0.5 altitude noise). Not sustained."
        },
        {
            "id": "D2",
            "sensor": "temperature",
            "time_seconds": f">{T_TEMP_OFFSET_START}",
            "description": "Temperature reads ~4C higher after 1800s.",
            "why_not_anomaly": "Documented calibration offset in calibration.json. Subtract 4.0C. Not an anomaly."
        },
        {
            "id": "D3",
            "sensor": "gps",
            "time_seconds": T_BAD_LAT_ROW,
            "description": "One row has lat=999.",
            "why_not_anomaly": "Malformed data. Drop the row. Not a flight anomaly."
        }
    ]
}
gt_path = os.path.join(OUT, "..", "ground_truth_PRIVATE.json")
with open(gt_path, "w") as f:
    json.dump(ground_truth, f, indent=2)
print(f"Wrote PRIVATE answer key: {gt_path}")

print("\nDone. Check the 'dataset' folder for student files.")
print("The private answer key is in ground_truth_PRIVATE.json (one level up).")