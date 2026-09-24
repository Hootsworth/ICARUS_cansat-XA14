# RVSAT-1 Interface Control Document (ICD)
**Document ID:** RVSAT-ICD-REV-B  
**Spacecraft Subsystems:** EPS, Thermal, ADCS, TT&C, CDH (OBC)  

---

## 1. Frame Structure (44 Bytes Fixed)

Every telemetry frame transmitted by RVSAT-1 is exactly **44 bytes** long.

```
+----------------+----------------+----------------+----------------+----------------+
| ASM (4B)       | SC ID (2B)     | Seq Num (2B)   | OBC Tick (2B)  | Type (1B)      |
| 1A CF FC E1    | 0x4256 ('RV')  | uint16 (BE)    | uint16 (LE!)   | 0x01 / 0x02    |
+----------------+----------------+----------------+----------------+----------------+
| Mode (1B)      | Bat V (2B)     | Bat I (2B)     | Solar I (2B)   | Bus V (2B)     |
| 0..3           | raw uint16     | int16 (mA)     | uint16 (mA)    | raw uint16     |
+----------------+----------------+----------------+----------------+----------------+
| Temp Bat (2B)  | Temp Pan (2B)  | Temp OBC (2B)  | Wheel RPMs(6B) | Gyro X,Y,Z(6B) |
| raw int16      | raw int16      | raw int16      | 3x int16       | 3x int16       |
+----------------+----------------+----------------+----------------+----------------+
| RSSI (1B)      | CPU (1B)       | Reset (1B)     | Flags (1B)     | CRC-16 (2B)    |
| int8 (dBm)     | uint8 (%)      | uint8 count    | bitfield       | CCITT-FALSE    |
+----------------+----------------+----------------+----------------+----------------+
```

### Detailed Field Mapping

| Offset | Size | Field Name | Data Type | Encoding | Physical Unit & Calibration |
|---|---|---|---|---|---|
| **0** | 4 | Attached Sync Marker (ASM) | bytes | Hex | `1A CF FC E1` |
| **4** | 2 | Spacecraft Identifier | uint16 | Big-Endian | Fixed `0x4256` ('RV') |
| **6** | 2 | Sequence Counter | uint16 | Big-Endian | Increments +1 per frame, rolls over at 65536 |
| **8** | 2 | OBC Tick Counter | uint16 | **Little-Endian** | 0.1s resolution counter. Wraps every 6553.6s |
| **10** | 1 | Frame Type | uint8 | Byte | `0x01`: HK Telemetry, `0x02`: TIME_SYNC |
| **11** | 1 | Spacecraft Mode | uint8 | Byte | `0`: Safe, `1`: Nominal, `2`: Payload, `3`: Detumble |
| **12** | 2 | Battery Voltage | uint16 | Big-Endian | $V_{bat} = 6000.0 + 0.05 \times \text{raw}$ (mV) |
| **14** | 2 | Battery Current | int16 | Big-Endian | mA (positive = charging, negative = discharging) |
| **16** | 2 | Solar Array Current | uint16 | Big-Endian | mA |
| **18** | 2 | Regulated Bus Voltage | uint16 | Big-Endian | $V_{bus} = 4500.0 + 0.04 \times \text{raw}$ (mV) |
| **20** | 2 | Battery Temperature | int16 | Big-Endian | $T_{bat} = (\text{raw} - 1000) / 100.0$ (°C) |
| **22** | 2 | Solar Panel Temperature | int16 | Big-Endian | $T_{panel} = (\text{raw} - 1000) / 100.0$ (°C) |
| **24** | 2 | OBC Internal Temperature| int16 | Big-Endian | $T_{obc} = (\text{raw} - 1050) / 100.0$ (°C) [Rev B] |
| **26** | 6 | Reaction Wheel RPM 1,2,3| 3x int16 | Big-Endian | RPM along X, Y, Z body axes |
| **32** | 6 | Gyroscope Rates X, Y, Z | 3x int16 | Big-Endian | Angular rate $\omega = \text{raw} \times 0.01$ (deg/s) |
| **38** | 1 | RSSI | int8 | Big-Endian | Receiver Signal Strength Indicator (dBm) |
| **39** | 1 | CPU Utilization | uint8 | Byte | Percent (0 to 100%) |
| **40** | 1 | OBC Reset Counter | uint8 | Byte | Boot count since mission inception |
| **41** | 1 | Telemetry Flags | uint8 | Bitfield | bit 0: `cmd_ack`, bit 1: `heater_on`, bit 2: `payload_on` |
| **42** | 2 | CRC-16/CCITT-FALSE | uint16 | Big-Endian | Checksum over bytes 4..41 (Poly `0x1021`, Init `0xFFFF`) |

---

## 2. TIME_SYNC Frames (Type 0x02)
- Frame Type byte (Offset 10) = `0x02`.
- Bytes 12..15 contain the 32-bit unsigned Unix epoch second (UTC).
- Bytes 16..41 are filled with `0x00`.
- CRC-16 (Bytes 42..43) is calculated over bytes 4..41 normally.

---

## 3. Diagnostic Fault Signature Codes

| Fault Code | Subsystem | Failure Mechanism & Symptoms |
|---|---|---|
| **EPS-01** | EPS | Solar array shunt switch short (0 mA solar current in full sunlight) |
| **EPS-03** | EPS | Photo-voltaic cell degradation (gradual current output decay) |
| **EPS-07** | EPS | Battery cell degradation / abrupt ~150 mV voltage step drop in eclipse |
| **THM-01** | Thermal | Heater thermostat open circuit (sub-zero battery in eclipse) |
| **THM-03** | Thermal | Heater switch stuck CLOSED; uncommanded temperature rise outside schedule |
| **ADCS-01** | ADCS | Reaction wheel tachometer noise / jitter |
| **ADCS-02** | ADCS | Reaction wheel motor lockup / freeze (variance=0), gyro step & OBC reset |
| **COM-01** | TT&C | Downlink low-noise amplifier gain degradation (-25 dBm permanent drop) |
| **COM-04** | TT&C | Single Event Upset (SEU) single bit-flip corruption in frame |
| **OBC-01** | CDH | Memory parity error |
| **OBC-02** | CDH | Watchdog timer reset |
