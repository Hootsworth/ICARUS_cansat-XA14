# Flight Operations Emergency Runbook: Spacecraft Anomaly Recovery
**Document ID:** OP-RB-88 (Revision 1.2)  
**Applicability:** Phase 4 Live Contingency Finale  

---

## 1. Initial Telemetry Interrogation
1. Open the Live Contingency Console.
2. Issue the `GET_HK` command to retrieve active telemetry:
   - Spacecraft Mode (Expected: `SAFE` / 0)
   - Bus Voltage (Nominal: ~4900..5050 mV)
   - Battery Temperature
   - Heater Status (Heaters A and B)
   - Reaction Wheel States & RPMs (Wheels 1, 2, 3)

---

## 2. Thermal Envelope Management
1. Inspect the reported **Battery Temperature**.
2. **CRITICAL SAFETY THRESHOLD:** If Battery Temperature exceeds **45.0 °C**:
   - You **MUST** immediately turn OFF the stuck heater using `HEATER A OFF` or `HEATER B OFF`.
   - **WARNING:** Attempting a Reaction Wheel Reset while battery temperature is > 45 °C will trigger a severe inrush current brownout (Bus Voltage drops to 3800 mV, triggering an uncommanded OBC reset with a **+300s sim penalty**).

---

## 3. ADCS Reaction Wheel Power Cycle
1. Identify the single faulted reaction wheel (reported with state `FAULT` and RPM `0`).
2. Issue the reset command: `WHEEL <1|2|3> RESET`.
3. **CAUTION:** Only reset the faulted wheel! Resetting an operational wheel will de-synchronize the ADCS bus and incur a **+300s sim penalty**.

---

## 4. Spin-Up & RPM Lock Verification (Revision 1.2 Note)
1. Following a wheel reset, the wheel transitions to `SPINNING_UP`.
2. **MANDATORY:** Ground flight operations require a **60-second waiting period** for the reaction wheel to reach nominal ~3150 RPM before mode transition.
3. Advance the simulation by 60s using `WAIT 60` (or wait in real time) and verify status with `GET_HK`.
4. *[TRAP NOTICE]: Revision 1.0 previously suggested issuing MODE NOMINAL immediately. Revision 1.2 supersedes this; immediate mode transition will be rejected by the flight computer.*

---

## 5. Transition to Nominal Mode
1. Ensure all heaters are in nominal states.
2. Ensure all three reaction wheels report `OPERATIONAL` status.
3. Transmit: `MODE NOMINAL`.
4. Upon successful validation, the flight computer will return the **Final Recovery Flag** and award speed bonus points.
