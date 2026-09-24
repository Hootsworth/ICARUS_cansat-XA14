# RVSAT-1 Satellite Telemetry & Flight Operations Challenge
**Complete Build and Run Playbook**  
*Built for 11 teams. Auto-graded, seeded telemetry datasets, chained encrypted packages, live downlink API, and real-time contingency finale.*

---

## 🛰️ Architecture & System Structure

```
├── config.py                 # Core constants, points, tolerances, timing & secrets
├── models.py                 # SQLite database schema (Teams, Submissions, Flags, Passes, Logs)
├── crypto_utils.py           # CRC-16/CCITT-FALSE, HMAC signing, AES/Zip packaging
├── generator/
│   ├── gen.py                # Multi-team dataset generator (Archives, Beacons, Dumps, Packages)
│   ├── telemetry_model.py    # Orbit physics, sensor baselines, calibration, clock drift
│   └── fault_engine.py       # Fault injection (F1..F4, decoys, cascade, bit-flips)
├── solver/
│   ├── solve.py              # Automated reference solver (tests all 11 seeds with 100% accuracy)
│   └── decoder.py            # 44-byte binary telemetry frame parser
├── app/
│   ├── main.py               # FastAPI application entry point
│   ├── auth.py               # Password hashing & token authentication
│   ├── routes_api.py         # Submissions, pass API, scoreboard API, credits, console
│   ├── routes_pages.py       # Dashboard, Challenge briefing, Packages, Scoreboard, Admin
│   ├── finale_engine.py      # Real-time live contingency state machine engine
│   ├── templates/            # Jinja2 HTML templates with RVU crest & Navy theme
│   └── static/               # CSS styles, print styling, JS utilities, SVG crest
├── docs/
│   ├── MISSION_HANDBOOK.md   # Participant Handbook (schedule, tools, rules, scoring)
│   ├── ICD.md                # 44-byte frame definition, calibrations, fault signature table
│   ├── PLANNED_SCHEDULE.md   # Planned operations schedule reference
│   ├── RUNBOOK_FINALE.md     # Emergency anomaly recovery runbook & traps
│   ├── RULES_CONDUCT.md      # Rules of conduct & AI policy
│   └── ERRATA_1200.md        # 12:00 UTC Errata release bulletin
├── run_generation.py         # One-click generator script
├── run_validation.py         # One-click solver verification harness
└── run_server.py             # One-click FastAPI server launcher
```

---

## 🚀 Quick Start Guide (Build & Run in 3 Steps)

### Step 1: Install Dependencies
```bash
pip install fastapi uvicorn numpy pandas pyzipper jinja2
```
*(Note: Pure standard library fallback is built into the engine if optional packages like `pyzipper` are not installed).*

### Step 2: Generate All 11 Team Datasets & Encrypted Packages
```bash
python run_generation.py
```
This produces:
- Full 24-hour binary archives (`archive.bin` = 86,400 frames per team) in `generated_data/server_archives/`.
- 1,440-minute beacon files (`beacon.csv`), sample dumps (`sample_dump.bin`), and planned schedules in `generated_data/teams/`.
- Chained encrypted zip packages (`phase1.zip`, `phase2.zip`, `phase3.zip`) locked by phase flags.
- Master answers and verification keys in `generated_data/answers/master_answers.json`.

### Step 3: Run Reference Solver Verification Harness
```bash
python run_validation.py
```
Validates that all 11 team seeds are mathematically solvable and pass **100% of challenges** within tolerance.

### Step 4: Launch Flight Operations Web Server
```bash
python run_server.py
```
- **Mission Dashboard & Login:** `http://localhost:8000`
- **Projector Scoreboard (Auto-polling):** `http://localhost:8000/scoreboard`
- **Flight Director Admin Console:** `http://localhost:8000/admin` (Password: `rvu_flight_ops_admin_2027`)

---

## ⏱️ Competition Timeline & Event Schedule

| Time | Event & Phase | Details |
|---|---|---|
| **10:30 – 11:00** | **Round 1: Launch Readiness Review** | 4 Stations (Hex decoding, Clock math, Strip charts, Go/No-Go). Hands-on sheets; awards extra downlink credits & Launch Auth Code. |
| **11:00 – 11:15** | **Briefing & Registration** | Teams register on portal with Team ID (1..11) and Join Code (`RVU-ORBIT-2027`). Receive Handbook & ICD. |
| **11:15 – 11:55** | **Phase 1: Signal Acquisition** | Teams decode 30-min raw dump (`sample_dump.bin`), calculate clock drift rate, locate data drop gap, and identify uint16 tick wrap. Solving yields Phase 1 Flag to unlock Phase 2 zip. |
| **11:55 – 12:45** | **Phase 2: Downlink Investigation** | Inspect 24h `beacon.csv`. Purchase 10-min passes via `POST /api/pass` using 12 credits. Isolate Faults F1 (EPS-07), F2 (THM-03), F3 (ADCS-02), F4 (COM-04). |
| **12:45 – 13:15** | **Phase 3: Fault Isolation** | In-depth anomaly analysis: F3 cascade parameter ordering, OBC reset timestamp, brute-force 1-bit CRC error recovery, F1 orbit voltage. |
| **Parallel** | **Bonus Track: Spoofed Telecommand** | Verify HMACs in `uplink_log.csv` using split key (Handbook Part A + Round 1 Card Part B) to isolate forged and replayed commands. |
| **13:00 – 13:30** | **Phase 4: Live Contingency Finale** | Admin triggers finale. Teams open `/console` to interactively recover faulted spacecraft using OP-RB-88 runbook. |
| **13:30 – 14:00** | **Scoreboard Freeze & Debrief** | Scoreboard frozen during final contingency. Reveal winners at 14:00 and walk through solution notebooks. |

---

## 🛡️ Anti-Cheat & AI Defence Architecture

1. **Downlink Credit Budget (12 Credits):** No single 24-hour file is handed over to feed into an LLM. Slices must be strategically purchased.
2. **Chained Encrypted Zip Packages:** Each phase package password is the previous phase's flag (`MISSION{...}`).
3. **Per-Team Deterministic Seeds:** All telemetry, timestamps, clock drift rates, fault onsets, and flags are unique to each team seed.
4. **Exact-Answer Auto-Grading:** Strict normalization, $\pm 1$s timestamp tolerances, 5-attempt limit, and 10-minute cooldowns prevent brute forcing.
5. **Data Traps & Errata:** Little-endian encoding on OBC tick counter inside a big-endian frame, oscillator ppm drift, uint16 rollover, and 12:00 UTC Revision B sensor calibration errata bulletin.

---

## 🖨️ Printing & Operations Checklist

- **Print Round 1 Sheets:** Navigate to `/round1-sheet/<team_id>` (e.g. `/round1-sheet/1` to `/round1-sheet/11`) and click **Print Sheet**.
- **Admin Password:** `rvu_flight_ops_admin_2027` (or configured in `config.py` / env var `RVSAT_ADMIN_PASSWORD`).
- **Event Join Code:** `RVU-ORBIT-2027`.
- **Projector Setup:** Open `http://<SERVER_IP>:8000/scoreboard` on the projector screen. It automatically updates every 10 seconds.
