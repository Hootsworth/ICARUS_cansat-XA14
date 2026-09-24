# RVSAT-1 Mission Participant Handbook
**Event:** Satellite Telemetry & Flight Operations Challenge  
**Spacecraft:** RVSAT-1 (3U Low-Earth Orbit Remote Sensing & Telemetry Testbed)  
**Organization:** RV University Flight Dynamics & Ground Station Network  

---

## 1. Mission Overview & Schedule

| Time Window | Mission Phase | Description |
|---|---|---|
| **10:30 – 11:00** | **Round 1: Launch Readiness Review** | 4 Hands-on Stations (7 min each). Earn extra downlink credits and Launch Authorisation Code. |
| **11:00 – 11:15** | **Mission Briefing** | Team registration on Flight Ops portal, ICD & Handbook distribution, countdown starts. |
| **11:15 – 11:55** | **Phase 1: Signal Acquisition** | Decode 30-min raw frame dump (`sample_dump.bin`), calculate clock drift, detect data drop, find uint16 tick wrap. |
| **11:55 – 12:45** | **Phase 2: Downlink Investigation** | Inspect 24h minutely beacon telemetry, purchase 10-min high-rate passes via API, isolate faults F1 to F4. |
| **12:45 – 13:15** | **Phase 3: Fault Isolation** | Detailed anomaly characterization: cascade sequencing, OBC reset timestamp, bit recovery, voltage calculation. |
| **Parallel** | **Bonus Track: Spoofed Telecommand** | Verify uplink HMAC signatures using split key (Handbook Part A + Round 1 Card Part B) to find forged and replayed commands. |
| **13:00 – 13:30** | **Phase 4: Live Contingency Finale** | Simultaneous interactive emergency recovery console. Follow flight runbook to restore RVSAT-1 to Nominal mode. |
| **13:30 – 14:00** | **Scoreboard Freeze & Debrief** | Submissions close; live walkthrough of all 11 teams' datasets using reference solver. |

---

## 2. Downlink Credit Budget & Pass API

High-rate 1 Hz telemetry is **not** handed over in one massive file. Teams manage a constrained downlink budget:

- **Starting Budget:** 12 Downlink Credits (+ up to 4 extra credits earned during Round 1).
- **Pass Size:** Each credit buys a **10-minute window (600 frames = 26.4 KB)** starting at any second $t \in [0, 86400)$ you specify.
- **Pass API Endpoint:**
  ```http
  POST /api/pass
  Authorization: Bearer <YOUR_API_TOKEN>
  Content-Type: application/json

  {
    "start_utc": "2027-03-14T05:20:00Z"
  }
  ```
- **Rate Limit:** 1 pass request per 20 seconds.
- **Deduplication:** Requesting the exact same `start_utc` window within 5 minutes is **0 credits** (free retry).

---

## 3. Scoring System & Rules

| Challenge | Subsystem / Task | Base Points |
|---|---|---|
| **C1.1** | Phase 1: Clock Drift Calculation (PPM) | 100 |
| **C1.2** | Phase 1: Telemetry Data Gap Identification | 100 |
| **C1.3** | Phase 1: Tick Rollover UTC Timestamp | 100 |
| **C2.1** | Phase 2: Fault 1 (EPS-07) Onset UTC & Code | 200 |
| **C2.2** | Phase 2: Fault 2 (THM-03) Onset UTC & Code | 200 |
| **C2.3** | Phase 2: Fault 3 (ADCS-02) Cascade Onset UTC & Code | 250 |
| **C2.4** | Phase 2: Fault 4 (COM-04) Corrupted Frame ID & Code | 200 |
| **C3.1** | Phase 3: Cascade Parameter Sequence Order | 200 |
| **C3.2** | Phase 3: OBC Reset Recovery Timestamp | 150 |
| **C3.3** | Phase 3: Bit Error Recovery & Original Voltage | 250 |
| **C3.4** | Phase 3: F1 Orbit Number & Post-Eclipse Voltage | 150 |
| **B1.1** | Bonus: Forged Telecommand ID | 150 |
| **B1.2** | Bonus: Replayed Telecommand ID | 100 |
| **FINALE** | Phase 4: Live Contingency Restoration | 500 (+ up to 200 Speed Bonus) |

### Scoring Modifiers:
1. **Time Decay Bonus:** Each challenge earns up to **+30%** bonus points, decaying linearly over 120 minutes from event start.
2. **First Solver Bonus:** The first team across all 11 teams to correctly solve a challenge receives a **+10%** bonus.
3. **Attempt Limits & Penalty:** Each challenge permits **5 attempts**. Each incorrect submission costs **-5%** of base points. Exceeding 5 wrong attempts activates a **10-minute cooldown**.
4. **Tie-Break:** Earliest server timestamp of the last correct submission.

---

## 4. Chained Encrypted Packages
Each phase's data is packaged in an encrypted zip archive:
- **Phase 1 Package:** Unlocked using your **Launch Authorisation Code** (from Round 1).
- **Phase 2 Package:** Unlocked using the **Phase 1 Flag** (`MISSION{...}`).
- **Phase 3 Package:** Unlocked using the **Phase 2 Flag** (`MISSION{...}`).

---

## 5. AI Policy & Integrity
- AI assistants (ChatGPT, Claude, Copilot, Gemini) are **allowed and encouraged** for code generation, plotting, and parsing.
- However, all datasets are uniquely generated with per-team seeds. Brute-forcing, scraping, or automated spamming will trigger security locks and disqualification.
