"""
API routes for Challenge Submissions, Pass Requests, Live Scoreboard, and Finale Console.
"""
import time
import json
import os
import struct
import base64
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, Response
from config import (
    TOTAL_TEAMS, MASTER_SECRET, MISSION_EPOCH, TOTAL_DURATION_S,
    FRAME_SIZE_BYTES, PASS_FRAME_COUNT, PASS_RATE_LIMIT_S, PASS_DEDUP_WINDOW_S,
    SERVER_ARCHIVES_DIR, ANSWERS_DIR, MAX_ATTEMPTS_PER_CHALLENGE, COOLDOWN_DURATION_S,
    WRONG_ATTEMPT_PENALTY_PCT, MAX_TIME_BONUS_PCT, TIME_BONUS_DECAY_WINDOW_S,
    FIRST_SOLVER_BONUS_PCT
)
from models import get_db_connection
from app.auth import get_team_by_api_token
from app.finale_engine import get_or_create_finale_state
from crypto_utils import generate_flag

api_router = APIRouter(prefix="/api")

# Rate limit tracking in memory: { team_id: last_pass_timestamp }
_LAST_PASS_REQUEST = {}

def get_current_team_from_request(request: Request):
    """Retrieves authenticated team from session cookie or Bearer token."""
    # 1. Check Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        team = get_team_by_api_token(token)
        if team:
            return team
            
    # 2. Check Session Cookie
    team_id = request.session.get("team_id")
    if team_id:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        team = cur.fetchone()
        conn.close()
        return team
        
    return None

def normalize_text(text: str) -> str:
    """Normalizes string answers."""
    return " ".join(text.strip().split())

def parse_iso_utc(iso_str: str) -> datetime:
    """Parses standard ISO UTC string."""
    iso_clean = iso_str.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(iso_clean).astimezone(timezone.utc)

def check_answer_correctness(challenge_id: str, submitted_raw: str, expected_dict: dict) -> bool:
    """Evaluates answer correctness with exact normalization and specified tolerances."""
    sub = normalize_text(submitted_raw)
    exp = normalize_text(expected_dict["answer"])
    alt = normalize_text(expected_dict.get("alt_answer", ""))
    t_type = expected_dict.get("type", "string")
    tolerance = expected_dict.get("tolerance", 0)
    
    if sub.upper() == exp.upper() or (alt and sub.upper() == alt.upper()):
        return True
        
    try:
        if t_type == "numeric":
            val_sub = float(sub)
            val_exp = float(exp)
            return abs(val_sub - val_exp) <= float(tolerance)
            
        elif t_type == "iso_time":
            dt_sub = parse_iso_utc(sub)
            dt_exp = parse_iso_utc(exp)
            return abs((dt_sub - dt_exp).total_seconds()) <= tolerance
            
        elif t_type == "iso_time_and_code":
            parts_sub = sub.split()
            parts_exp = exp.split()
            if len(parts_sub) == 2 and len(parts_exp) == 2:
                dt_sub = parse_iso_utc(parts_sub[0])
                dt_exp = parse_iso_utc(parts_exp[0])
                time_ok = abs((dt_sub - dt_exp).total_seconds()) <= tolerance
                code_ok = (parts_sub[1].upper() == parts_exp[1].upper())
                return time_ok and code_ok
                
        elif t_type == "iso_time_and_val":
            parts_sub = sub.replace("s", "").split()
            parts_exp = exp.replace("s", "").split()
            if len(parts_sub) == 2 and len(parts_exp) == 2:
                dt_sub = parse_iso_utc(parts_sub[0])
                dt_exp = parse_iso_utc(parts_exp[0])
                val_sub = float(parts_sub[1])
                val_exp = float(parts_exp[1])
                return abs((dt_sub - dt_exp).total_seconds()) <= tolerance and abs(val_sub - val_exp) <= 1
                
        elif t_type == "index_and_mV":
            parts_sub = sub.split()
            parts_exp = exp.split()
            if len(parts_sub) == 2 and len(parts_exp) == 2:
                idx_sub = int(parts_sub[0])
                idx_exp = int(parts_exp[0])
                v_sub = float(parts_sub[1])
                v_exp = float(parts_exp[1])
                return (idx_sub == idx_exp) and (abs(v_sub - v_exp) <= tolerance)
                
        elif t_type == "orbit_and_mV":
            parts_sub = sub.split()
            parts_exp = exp.split()
            if len(parts_sub) == 2 and len(parts_exp) == 2:
                orb_sub = int(parts_sub[0])
                orb_exp = int(parts_exp[0])
                v_sub = float(parts_sub[1])
                v_exp = float(parts_exp[1])
                return (orb_sub == orb_exp) and (abs(v_sub - v_exp) <= tolerance)
    except Exception:
        return False
        
    return False

# -----------------------------------------------------------------------------
# SUBMIT ENDPOINT
# -----------------------------------------------------------------------------
@api_router.post("/submit")
async def submit_challenge(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required. Please login or provide Bearer API token.")
        
    body = await request.json()
    challenge_id = body.get("challenge_id", "").strip().upper()
    answer_raw = body.get("answer", "").strip()
    
    if not challenge_id or not answer_raw:
        raise HTTPException(status_code=400, detail="Missing challenge_id or answer.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Verify Challenge exists
    cur.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
    ch = cur.fetchone()
    if not ch:
        conn.close()
        raise HTTPException(status_code=404, detail="Challenge ID not found.")
        
    # Round 2 is staged. Do not allow direct jumps into sealed evidence phases.
    if ch["round_id"] == 2:
        conn.close()
        if ch["phase"] == "PHASE_2":
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM flags WHERE team_id = ? AND phase = 'PHASE_1'", (team["id"],))
            unlocked = cur.fetchone()
            if not unlocked:
                conn.close()
                raise HTTPException(status_code=403, detail="Phase 2 is sealed. Complete Phase 1 first.")
        elif ch["phase"] == "PHASE_3":
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM flags WHERE team_id = ? AND phase = 'PHASE_2'", (team["id"],))
            unlocked = cur.fetchone()
            if not unlocked:
                conn.close()
                raise HTTPException(status_code=403, detail="Phase 3 is sealed. Complete Phase 2 first.")
        elif ch["phase"] == "BONUS":
            conn = get_db_connection()
            cur = conn.cursor()
        # Continue with the normal submission flow using a fresh connection.
    # 2. Check if already solved correctly
    cur.execute("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ? AND correct = 1", (team["id"], challenge_id))
    existing_correct = cur.fetchone()
    if existing_correct:
        conn.close()
        return JSONResponse({
            "status": "already_solved",
            "message": f"Challenge {challenge_id} is already solved! Points: {existing_correct['points_awarded']}",
            "points_awarded": existing_correct["points_awarded"]
        })
        
    # 3. Check attempts and cooldowns
    cur.execute("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ? ORDER BY ts_utc_ms DESC", (team["id"], challenge_id))
    attempts = cur.fetchall()
    now_ms = int(time.time() * 1000)
    
    wrong_attempts = len(attempts)
    if wrong_attempts >= MAX_ATTEMPTS_PER_CHALLENGE:
        last_attempt_ts = attempts[0]["ts_utc_ms"]
        elapsed_s = (now_ms - last_attempt_ts) / 1000.0
        if elapsed_s < COOLDOWN_DURATION_S:
            remaining_cd = int(COOLDOWN_DURATION_S - elapsed_s)
            conn.close()
            return JSONResponse(status_code=429, content={
                "status": "cooldown",
                "message": f"Maximum attempt limit ({MAX_ATTEMPTS_PER_CHALLENGE}) reached. Cooldown active. Try again in {remaining_cd}s.",
                "cooldown_remaining_s": remaining_cd
            })
            
    # 4. Load Master Answers
    answers_file = os.path.join(ANSWERS_DIR, "master_answers.json")
    with open(answers_file, "r", encoding="utf-8") as f:
        master_answers = json.load(f)
        
    team_answers = master_answers.get(str(team["id"]))
    if not team_answers:
        conn.close()
        raise HTTPException(status_code=500, detail="Team master answers not found.")
        
    expected_data = team_answers["challenges"].get(challenge_id)
    if not expected_data:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No answer key for challenge {challenge_id}.")
        
    # 5. Evaluate answer
    is_correct = check_answer_correctness(challenge_id, answer_raw, expected_data)
    attempt_no = wrong_attempts + 1
    
    points_awarded = 0
    time_bonus = 0
    first_solver_bonus = 0
    flag_unlocked = None
    
    if is_correct:
        base_points = ch["points"]
        # Wrong attempt penalty: -5% per previous failed attempt
        penalty_factor = max(0.0, 1.0 - (wrong_attempts * WRONG_ATTEMPT_PENALTY_PCT))
        calc_points = int(base_points * penalty_factor)
        
        # Time decay bonus: up to +30%
        # Decays linearly from competition start over 120 minutes
        time_elapsed_s = time.time() - (MISSION_EPOCH.timestamp() if False else time.time() - 600)
        decay_factor = max(0.0, 1.0 - (time_elapsed_s / TIME_BONUS_DECAY_WINDOW_S))
        time_bonus = int(base_points * MAX_TIME_BONUS_PCT * decay_factor)
        
        # First solver bonus: check if any other team has solved this challenge
        cur.execute("SELECT COUNT(*) as count FROM submissions WHERE challenge_id = ? AND correct = 1", (challenge_id,))
        first_check = cur.fetchone()
        if first_check["count"] == 0:
            first_solver_bonus = int(base_points * FIRST_SOLVER_BONUS_PCT)
            
        points_awarded = calc_points + time_bonus + first_solver_bonus
        
        # Check Phase Completion & Release Flags
        phase = ch["phase"]
        cur.execute("SELECT id FROM challenges WHERE phase = ?", (phase,))
        all_phase_chs = [r["id"] for r in cur.fetchall()]
        
        cur.execute("SELECT challenge_id FROM submissions WHERE team_id = ? AND correct = 1", (team["id"],))
        solved_chs = [r["challenge_id"] for r in cur.fetchall()]
        solved_chs.append(challenge_id)
        
        if all(c_id in solved_chs for c_id in all_phase_chs):
            # Phase is completed! Release flag
            flag_unlocked = team_answers["flags"].get(phase)
            if flag_unlocked:
                cur.execute("""
                INSERT OR REPLACE INTO flags (team_id, phase, flag, released_at)
                VALUES (?, ?, ?, ?)
                """, (team["id"], phase, flag_unlocked, datetime.now(timezone.utc).isoformat()))
                
    # Record the submission against the challenge's owning round.
    challenge_round = ch["round_id"]
    cur.execute("""
    INSERT INTO submissions (team_id, round_id, challenge_id, answer, correct, points_awarded, ts_utc_ms, attempt_no)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (team["id"], challenge_round, challenge_id, answer_raw, 1 if is_correct else 0, points_awarded, now_ms, attempt_no))

    # Keep the owning round's score in sync.
    cur.execute("""
    INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at)
    VALUES (?, ?, 'active', (SELECT COALESCE(SUM(points_awarded), 0) FROM submissions WHERE team_id = ? AND round_id = ? AND correct = 1), ?)
    """, (team["id"], challenge_round, team["id"], challenge_round, datetime.now(timezone.utc).isoformat()))

    # Round 2 is the main investigation. Completing C1-C3 unlocks Round 3.
    if is_correct and challenge_round == 2:
        cur.execute("""
        SELECT id FROM challenges
        WHERE round_id = 2 AND phase IN ('PHASE_1', 'PHASE_2', 'PHASE_3')
        """)
        required_ids = {row["id"] for row in cur.fetchall()}
        cur.execute("""
        SELECT challenge_id FROM submissions
        WHERE team_id = ? AND round_id = 2 AND correct = 1
        """, (team["id"],))
        solved_ids = {row["challenge_id"] for row in cur.fetchall()}
        if required_ids.issubset(solved_ids):
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute("""
            UPDATE round_status
            SET status = 'submitted', submitted_at = ?, score = (
                SELECT COALESCE(SUM(points_awarded), 0) FROM submissions
                WHERE team_id = ? AND round_id = 2 AND correct = 1
            )
            WHERE team_id = ? AND round_id = 2
            """, (now_iso, team["id"], team["id"]))
            cur.execute("""
            INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at)
            VALUES (?, 3, 'active', 0, ?)
            """, (team["id"], now_iso))
            cur.execute("""
            INSERT INTO events (kind, detail, ts_utc_ms)
            VALUES ('ROUND2_COMPLETED', ?, ?)
            """, (f"Team {team['id']} completed the main telemetry investigation.", now_ms))

    conn.commit()
    conn.close()
    
    if is_correct:
        return JSONResponse({
            "status": "correct",
            "message": f"Correct! +{points_awarded} points awarded.",
            "points_awarded": points_awarded,
            "time_bonus": time_bonus,
            "first_solver_bonus": first_solver_bonus,
            "flag_unlocked": flag_unlocked
        })
    else:
        remaining_attempts = max(0, MAX_ATTEMPTS_PER_CHALLENGE - attempt_no)
        return JSONResponse(status_code=400, content={
            "status": "incorrect",
            "message": f"Incorrect answer. {remaining_attempts} attempts remaining before cooldown.",
            "remaining_attempts": remaining_attempts
        })

# -----------------------------------------------------------------------------
# PASS API ENDPOINT (Downlink Budget)
# -----------------------------------------------------------------------------
@api_router.post("/pass")
async def request_telemetry_pass(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required. Provide Bearer API token in Authorization header.")
        
    team_id = team["id"]
    now_time = time.time()
    now_ms = int(now_time * 1000)
    
    # 1. Enforce Rate Limit: 1 pass per 20 seconds
    last_pass_time = _LAST_PASS_REQUEST.get(team_id, 0)
    if (now_time - last_pass_time) < PASS_RATE_LIMIT_S:
        retry_after = int(PASS_RATE_LIMIT_S - (now_time - last_pass_time))
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "message": f"Please wait {retry_after}s before next pass request."}
        )
        
    body = await request.json()
    start_utc_str = body.get("start_utc", "").strip()
    if not start_utc_str:
        raise HTTPException(status_code=400, detail="Missing 'start_utc' parameter (e.g. '2027-03-14T05:20:00Z').")
        
    try:
        req_dt = parse_iso_utc(start_utc_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ISO UTC format for 'start_utc'. Expected: YYYY-MM-DDTHH:MM:SSZ")
        
    # Calculate offset in 24h archive (0..86400 seconds)
    start_sec = int((req_dt - MISSION_EPOCH).total_seconds())
    if start_sec < 0 or start_sec >= TOTAL_DURATION_S:
        raise HTTPException(status_code=400, detail=f"Requested timestamp {start_utc_str} is outside mission window (0 to 86400s).")
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 2. Check Deduplication: repeating exact same start_utc within 5 min (300s) is free!
    cur.execute("""
    SELECT * FROM passes 
    WHERE team_id = ? AND start_utc = ? AND (? - ts_utc_ms) < ?
    ORDER BY ts_utc_ms DESC LIMIT 1
    """, (team_id, start_utc_str, now_ms, PASS_DEDUP_WINDOW_S * 1000))
    existing_pass = cur.fetchone()
    
    credits_to_charge = 1
    if existing_pass:
        credits_to_charge = 0 # Free retry!
    else:
        # Check credit balance
        cur.execute("SELECT credits FROM teams WHERE id = ?", (team_id,))
        curr_credits = cur.fetchone()["credits"]
        if curr_credits < 1:
            conn.close()
            return JSONResponse(status_code=402, content={
                "error": "Insufficient credits",
                "message": "You have 0 downlink credits remaining. Trade or earn credits from Flight Operations."
            })
        # Deduct 1 credit
        cur.execute("UPDATE teams SET credits = credits - 1 WHERE id = ?", (team_id,))
        
    # Record pass
    cur.execute("""
    INSERT INTO passes (team_id, start_utc, frames_count, credits_charged, ts_utc_ms)
    VALUES (?, ?, ?, ?, ?)
    """, (team_id, start_utc_str, PASS_FRAME_COUNT, credits_to_charge, now_ms))
    conn.commit()
    
    # Update rate limit tracker
    _LAST_PASS_REQUEST[team_id] = now_time
    
    # Read 600 frames (26,400 bytes) from server archive
    archive_path = os.path.join(SERVER_ARCHIVES_DIR, f"team_{team_id:02d}_archive.bin")
    if not os.path.exists(archive_path):
        conn.close()
        raise HTTPException(status_code=500, detail="Server telemetry archive not found.")
        
    with open(archive_path, "rb") as f_arch:
        f_arch.seek(start_sec * FRAME_SIZE_BYTES)
        raw_pass_bytes = f_arch.read(PASS_FRAME_COUNT * FRAME_SIZE_BYTES)
        
    cur.execute("SELECT credits FROM teams WHERE id = ?", (team_id,))
    updated_credits = cur.fetchone()["credits"]
    conn.close()
    
    # Return binary frames with metadata headers
    headers = {
        "X-Credits-Charged": str(credits_to_charge),
        "X-Credits-Remaining": str(updated_credits),
        "X-Frames-Count": str(len(raw_pass_bytes) // FRAME_SIZE_BYTES),
        "Content-Disposition": f'attachment; filename="pass_{team_id}_{start_sec}.bin"'
    }
    return Response(content=raw_pass_bytes, media_type="application/octet-stream", headers=headers)

# -----------------------------------------------------------------------------
# CREDITS & SCOREBOARD ENDPOINTS
# -----------------------------------------------------------------------------
@api_router.get("/credits")
async def get_team_credits(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT credits FROM teams WHERE id = ?", (team["id"],))
    credits = cur.fetchone()["credits"]
    
    cur.execute("SELECT * FROM passes WHERE team_id = ? ORDER BY ts_utc_ms DESC", (team["id"],))
    passes = [dict(p) for p in cur.fetchall()]
    conn.close()
    
    return {"team_id": team["id"], "credits": credits, "passes_count": len(passes), "recent_passes": passes[:10]}

@api_router.get("/scoreboard")
async def get_scoreboard(request: Request):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if scoreboard is frozen
    cur.execute("SELECT value FROM app_state WHERE key = 'scoreboard_frozen'")
    is_frozen = (cur.fetchone()["value"] == "true")
    
    cur.execute("SELECT id, name, seed FROM teams ORDER BY id")
    teams = cur.fetchall()
    
    # Submissions for Round 4
    cur.execute("SELECT * FROM submissions WHERE correct = 1 ORDER BY ts_utc_ms ASC")
    all_solves = cur.fetchall()
    
    # Round status for Rounds 1 and 2 ONLY (Round 3 is strictly secret!)
    cur.execute("SELECT team_id, round_id, score, status, submitted_at FROM round_status WHERE round_id IN (1, 2)")
    round_rows = cur.fetchall()
    round_scores = {}
    for r in round_rows:
        if r["status"] == "submitted":
            round_scores[(r["team_id"], r["round_id"])] = r["score"]
    
    cur.execute("SELECT * FROM flags")
    all_flags = cur.fetchall()
    conn.close()
    
    standings = []
    for tm in teams:
        t_id = tm["id"]
        t_solves = [s for s in all_solves if s["team_id"] == t_id]
        t_flags = [f for f in all_flags if f["team_id"] == t_id]
        
        r1_pts = round_scores.get((t_id, 1), 0)
        r2_pts = round_scores.get((t_id, 2), 0)
        r4_pts = sum(s["points_awarded"] for s in t_solves)
        total_pts = r1_pts + r2_pts + r4_pts
        
        last_solve_ts = max([s["ts_utc_ms"] for s in t_solves], default=0)
        
        phase_progress = {
            "PHASE_1": sum(1 for s in t_solves if s["challenge_id"].startswith("C1")),
            "PHASE_2": sum(1 for s in t_solves if s["challenge_id"].startswith("C2")),
            "PHASE_3": sum(1 for s in t_solves if s["challenge_id"].startswith("C3")),
            "BONUS": sum(1 for s in t_solves if s["challenge_id"].startswith("B1")),
            "FINALE": sum(1 for s in t_solves if s["challenge_id"] == "FINALE")
        }
        
        standings.append({
            "team_id": t_id,
            "team_name": tm["name"],
            "total_points": total_pts,
            "r1_points": r1_pts,
            "r2_points": r2_pts,
            "r4_points": r4_pts,
            "solved_count": len(t_solves),
            "flags_unlocked": len(t_flags),
            "phase_progress": phase_progress,
            "last_solve_ts": last_solve_ts
        })
        
    # Sort by Total Points (DESC), then Last Solve Timestamp (ASC - earlier wins tie-break)
    standings.sort(key=lambda x: (-x["total_points"], x["last_solve_ts"] if x["last_solve_ts"] > 0 else 9999999999999))
    
    for rank, item in enumerate(standings, 1):
        item["rank"] = rank
        
    return {
        "frozen": is_frozen,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "standings": standings
    }

# -----------------------------------------------------------------------------
# LIVE FINALE CONSOLE ENDPOINT
# -----------------------------------------------------------------------------
@api_router.post("/console")
async def execute_console_command(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    body = await request.json()
    cmd = body.get("cmd", "").strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Missing command.")
        
    finale_state = get_or_create_finale_state(team["id"], team["seed"])
    res = finale_state.process_command(cmd)
    
    conn = get_db_connection()
    cur = conn.cursor()
    now_ms = int(time.time() * 1000)
    
    # Log command
    cur.execute("""
    INSERT INTO console_log (team_id, cmd, sim_time_sec, response, ts_utc_ms)
    VALUES (?, ?, ?, ?, ?)
    """, (team["id"], cmd, int(finale_state.get_elapsed_sim_sec()), res["output"], now_ms))
    
    # If finale recovered, award points and mark challenge FINALE as solved!
    if res.get("recovered"):
        base_pts = 500
        speed_bonus = res.get("speed_bonus", 0)
        total_awarded = base_pts + speed_bonus
        
        # Check if already recorded
        cur.execute("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = 'FINALE' AND correct = 1", (team["id"],))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO submissions (team_id, challenge_id, answer, correct, points_awarded, ts_utc_ms, attempt_no)
            VALUES (?, 'FINALE', 'NOMINAL_RESTORED', 1, ?, ?, 1)
            """, (team["id"], total_awarded, now_ms))
            
            cur.execute("""
            INSERT OR REPLACE INTO flags (team_id, phase, flag, released_at)
            VALUES (?, 'FINALE', ?, ?)
            """, (team["id"], res["final_flag"], datetime.now(timezone.utc).isoformat()))
            
    conn.commit()
    conn.close()
    
    return res
