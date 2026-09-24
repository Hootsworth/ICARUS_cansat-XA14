# ICARUS Telemetry Dataset

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
