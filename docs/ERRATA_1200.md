# Flight Director Errata Bulletin
**Release Timestamp:** 2027-03-14T12:00:00Z  
**Distribution:** All Ground Stations (Teams 1 through 11)  
**Classification:** Critical Flight Operations Notice  

---

## Bulletin Item 01: OBC Temperature Sensor Calibration
Attention all flight teams:

Ground station calibration testing has identified that the internal On-Board Computer (OBC) Temperature sensor (Bytes 24..25 in the 44-byte frame) is calibrated according to **Revision B** specifications:

$$\text{Temp}_{\text{OBC}} = \frac{\text{raw} - 1050}{100.0} \quad (^\circ\text{C})$$

*(Note: Battery and Solar Panel Temperature sensors continue to use the baseline Revision A offset of 1000).*

Please update your telemetry decoding and temperature conversion scripts accordingly.
