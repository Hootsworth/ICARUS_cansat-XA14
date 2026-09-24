# ICARUS Unified 4-Round Competition Portal Setup & Operations Guide

This guide details how to configure, administer, and execute the unified 4-round competition portal for the **ICARUS CanSat & Satellite Telemetry Challenge**.

---

## 1. Quick Start & Environment Installation

### Step 1: Create Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required dependencies
pip install fastapi uvicorn numpy pandas pyzipper jinja2
```

### Step 2: Initialize & Migrate Database Schema
```bash
python run_migration.py
```
This script safely establishes all 4 round tables (`rounds`, `round_status`, `quiz_questions`, `quiz_sessions`, `quiz_responses`, `game_sessions`), adds `round_id` foreign keys, and seeds an initial bank of aerospace/telemetry quiz questions.

### Step 3: (Optional) Generate Telemetry Archives
If executing Round 4 with generated binary archives:
```bash
python run_generation.py
```

### Step 4: Launch Flight Operations Web Server
```bash
python run_server.py
```
- **Team Portal:** `http://localhost:8000` (Join Code: `RVU-ORBIT-2027`)
- **Public Scoreboard (Projector Mode):** `http://localhost:8000/scoreboard`
- **Flight Director Admin Console:** `http://localhost:8000/admin` (Password: `rvu_flight_ops_admin_2027`)

---

## 2. The 4 Rounds & Data Flow

```
[Round 1: Mission Briefing] (Physical paper puzzle / cipher dossier)
       ↓ Submit Launch Authorisation Code
[Round 2: Rapid Flight Quiz] (15 questions, 25s server timer, speed bonus)
       ↓ Complete all 15 questions
[Round 3: Mission Ops Mini-Game] (Canvas simulation, HMAC-signed telemetry, secret score)
       ↓ HMAC verified & sealed
[Round 4: Telemetry Analysis] (Downlink pass API, binary forensics, live finale)
```

---

## 3. Configuring Round Timings & Progression

### Database Timing Controls
Round availability is governed by timestamps in the `rounds` table in `challenge.db`:
```sql
-- View all round gates
SELECT id, name, type, opens_at, closes_at, prerequisite_round_id FROM rounds;

-- Example: Set Round 2 to open at 11:30 UTC and close at 12:00 UTC
UPDATE rounds SET opens_at = '2027-03-14T11:30:00Z', closes_at = '2027-03-14T12:00:00Z' WHERE id = 2;
```

### Live Flight Director Overrides (Admin Console)
If you want to manually pause, force-open, or override prerequisites during the live event:
1. Log into `http://localhost:8000/admin`.
2. Under **Round Activation & Competition Control Cards**, click **Toggle Round X** to instantly enable or disable any round across the entire competition in real time.

---

## 4. Managing the Round 2 Quiz Question Pool

Round 2 selects 15 randomized questions per team from `quiz_questions`.

### Question Schema
Each question in `quiz_questions` contains:
- `prompt`: Question text
- `options`: JSON-encoded array of 4 choices (e.g. `["Option A", "Option B", "Option C", "Option D"]`)
- `correct_answer`: The exact matching text of the correct choice
- `difficulty`: `easy`, `medium`, or `hard`
- `pool_tag`: Categorization tag (e.g., `trajectory`, `avionics`, `telemetry`, `power`, `orbit`)

### Adding Questions via SQL
You can insert additional custom questions into `challenge.db`:
```python
import sqlite3, json

conn = sqlite3.connect("challenge.db")
cur = conn.cursor()

new_questions = [
    ("What component decouples the CanSat from the rocket payload bay?",
     json.dumps(["Deployment Piston / Spring Ejection Mechanism", "Pitot Tube", "Thermal Knife", "Solar Array"]),
     "Deployment Piston / Spring Ejection Mechanism", "easy", "recovery"),
    ("Which radio modulation is most commonly used for long-range CanSat low-bitrate links?",
     json.dumps(["LoRa (Chirp Spread Spectrum)", "QAM-256", "OFDM", "DVB-S2"]),
     "LoRa (Chirp Spread Spectrum)", "easy", "telemetry")
]

for prompt, opts, ans, diff, tag in new_questions:
    cur.execute("INSERT INTO quiz_questions (prompt, options, correct_answer, difficulty, pool_tag) VALUES (?, ?, ?, ?, ?)",
                (prompt, opts, ans, diff, tag))

conn.commit()
conn.close()
```

### Server Timing & Scoring Formula
- **Time Limit:** 25.0 seconds per question with a 2.5-second network grace window.
- **Scoring:**
  $$\text{Points} = 100 + \left\lfloor 50 \times \frac{T_{\text{remaining}}}{T_{\text{limit}}} \right\rfloor \quad (\text{if correct, else } 0)$$
- Responses submitted in $<600\text{ ms}$ automatically trigger a `TIMING_ANOMALY` entry in the `events` table for admin review.

---

## 5. Round 3 Secret Scoring & Anti-Cheat Architecture

### How the Secret Scoring Works
- **Storage:** Round 3 raw scores ($0 \dots 500$) are recorded in the `game_sessions` and `round_status` database tables.
- **Zero Leakage:**
  - The team-facing submission response (`/api/round3/submit`) returns `{ "status": "verified" }` with **zero score information**.
  - The team dashboard (`/dashboard`) explicitly purges Round 3 scores before rendering.
  - The public scoreboard (`/scoreboard` and `/api/scoreboard`) computes totals as:
    $$\text{Public Score} = \text{Round 1} + \text{Round 2} + \text{Round 4}$$
- **Admin Visibility:** The Flight Director Admin Console (`/admin`) surfaces:
  - The master table showing both **Grand Total (All 4)** and **Public Total**.
  - The dedicated **Round 3 Cryptographic Game Sessions** ledger with exact raw scores, survived orbits, and HMAC verification badges.

### Cryptographic HMAC Score Verification
When a team plays the Canvas mini-game:
1. Client requests a session: `POST /api/round3/session/start`.
2. Server derives a unique `session_token` via HMAC-SHA256 from `MASTER_SECRET` bound to the team and timestamp.
3. On game completion, the browser calculates:
   $$\text{Signature} = \text{HMAC-SHA256}(K_{\text{session}}, \text{"r3:\{session\_id\}:\{raw\_score\}:\{orbits\}:\{actions\}"})$$
4. The backend verifies the HMAC signature using constant-time string comparison (`hmac.compare_digest`). Submissions with invalid signatures or play durations under 20 seconds are rejected and logged under `SECURITY_ALERT`.

---

## 6. End-to-End Dry Run Instructions (Testing with Dummy Teams)

Follow this 5-minute procedure to verify all 4 rounds before real teams arrive:

### Step 1: Register Dummy Team
1. Open `http://localhost:8000/register` in your browser.
2. Register:
   - **Team ID:** `1`
   - **Team Name:** `Orion Flight Group`
   - **Password:** `testpass123`
   - **Join Code:** `RVU-ORBIT-2027`
3. You will be redirected to the Unified Dashboard (`/dashboard`).

### Step 2: Test Round 1 (Mission Briefing Gate)
1. In the **Round 1: Mission Briefing** card, notice the gated input field.
2. Enter an incorrect code (e.g. `TEST-WRONG`) and click **Verify Auth Code**. Verify that it rejects the submission.
3. Open `http://localhost:8000/admin` in an incognito window (Password: `rvu_flight_ops_admin_2027`). Look at Team 1's assigned `launch_auth_code` (e.g. `AUTH-IC338` or `AUTH-RV...`).
4. Enter the correct code into the Round 1 box and submit.
5. Verify:
   - Card updates to `✓ VERIFIED (+100 PTS)`.
   - **Round 2** changes from `LOCKED` to `ACTIVE`.

### Step 3: Test Round 2 (Rapid Flight Quiz)
1. Click **Start Quiz &rarr;** on the Round 2 card (opens `/round2`).
2. Click **Begin Round 2**.
3. Verify that the 25-second server-authoritative timer counts down with color transitions.
4. Answer several questions (test both correct and incorrect answers).
5. At the 15th question, verify that the quiz completes, displays your total score, and updates Round 2 status.
6. Return to `/dashboard` and verify that **Round 3** is now unlocked.

### Step 4: Test Round 3 (Mission Ops Mini-Game & Secret Scoring)
1. Click **Launch Flight &rarr;** on Round 3 (opens `/round3`).
2. Click **Initiate Orbital Flight**.
3. Manage Power, Thermal, and Fuel using keys `[1]`, `[2]`, `[3]`, and `[SPACE]`.
4. Allow the simulation to run through the 3 orbits.
5. Upon completion, verify:
   - The simulation displays `TELEMETRY FLIGHT LOG SEALED`.
   - **No numerical score is visible anywhere on the team's screen**.
6. Open the public scoreboard at `http://localhost:8000/scoreboard`.
   - Verify that Team 1's displayed score includes Round 1 (100) + Round 2 Quiz score, and that Round 3 is **completely absent** from the public table.
7. Open the Admin Console at `http://localhost:8000/admin`.
   - Verify that Team 1's secret Round 3 score (e.g. `+380 PTS`) appears in the **Master 4-Round Flight Standings** and in the **Round 3 Cryptographic Game Sessions** table with `✓ HMAC Signature Verified`.
   - Check the **Security & Anti-Cheat Audit Ledger** to ensure timing and event logging are healthy.

### Step 5: Test Round 4 (Telemetry Forensics)
1. Scroll down to the **Round 4: Satellite Telemetry Analysis** section on `/dashboard`.
2. Click any challenge (e.g. `C1.1`) to verify submission and grading functions.
