# Planned Operations Schedule Reference
**Document ID:** RVSAT-OPS-SCHED-01  
**Mission Window:** 2027-03-14T00:00:00Z to 2027-03-15T00:00:00Z (24 Hours)  

---

## 1. Description of Planned Events (Decoys & Scheduled Operations)

The flight plan for RVSAT-1 includes nominal scheduled maintenance windows and ground station passes. Anomalies are **unplanned** excursions not present in this schedule.

| Event Type | Typical Interval | Characteristics & Telemetry Signatures |
|---|---|---|
| **ECLIPSE TRANSITION** | Every 5700s (Starts at $t = 3600\text{s}$) | Solar current drops to 0 mA; battery voltage declines along standard discharge curve. |
| **GROUND STATION PASS** | 600s duration | High RSSI (-85 to -65 dBm); ground tracking active. |
| **GS HANDOVER** | 20s duration | RSSI dips to -115 dBm; short frame transmission gap expected. |
| **PLANNED SAFE MODE 1 & 2** | ~600s duration | Commanded Safe Mode test; `cmd_ack` flag (bit 0) is set (`0x01`). Mode = 0. |
| **PAYLOAD ACTIVATION** | ~1200s duration | Spectrometer powered; `payload_on` flag (bit 2) set (`0x04`). Battery current drops by 300 mA; Temp OBC rises +3.2 °C. |
| **PLANNED HEATER WINDOW** | ~900s duration | Planned thermal maintenance; `heater_on` flag (bit 1) set (`0x02`). Battery current drops by 250 mA; Temp Battery rises +4 °C. |

---

*Note: Each flight team receives a team-specific `planned_schedule.csv` in their Phase 2 Package with the exact scheduled timestamps for their satellite.*
