"""
Routes for Firebase Authentication and Multi-Computer Real-Time State Synchronization.
Supports Google OAuth, Anonymous Workstation Entry, and Remote Timer Commands.
"""
import os
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from config import ANSWERS_DIR, TOTAL_TEAMS, ADMIN_PASSWORD
from models import get_db_connection
from app.auth import hash_password

router = APIRouter()

@router.get("/api/competition/state")
async def get_competition_state():
    """
    Returns current multi-computer synchronized competition state.
    Used for local fallback polling and state bootstrap.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_state")
    rows = cur.fetchall()
    conn.close()

    state = {row["key"]: row["value"] for row in rows}

    timer_ends_at = int(state.get("competition_timer_ends_at", 0))
    timer_duration_s = int(state.get("competition_timer_duration_s", 1200))
    timer_running = state.get("competition_timer_running", "false") == "true"
    active_round = int(state.get("competition_active_round", 1))
    timer_title = state.get("competition_timer_title", "ROUND 1: BRIEFING")
    announcement = state.get("competition_announcement", "")
    announcement_id = state.get("competition_announcement_id", "")
    scoreboard_frozen = state.get("scoreboard_frozen", "false") == "true"

    # Compute remaining time
    now_ms = int(time.time() * 1000)
    remaining_s = max(0, int((timer_ends_at - now_ms) / 1000)) if timer_running else 0

    return {
        "status": "ok",
        "timer_running": timer_running,
        "timer_title": timer_title,
        "timer_ends_at": timer_ends_at,
        "timer_duration_s": timer_duration_s,
        "remaining_s": remaining_s,
        "active_round": active_round,
        "announcement": announcement,
        "announcement_id": announcement_id,
        "scoreboard_frozen": scoreboard_frozen,
        "server_time_ms": now_ms
    }


@router.post("/api/admin/competition/state")
async def update_competition_state(request: Request):
    """
    Flight Director remote timer and broadcast command endpoint.
    Accepts updates from the admin console on a separate laptop.
    """
    is_admin = request.session.get("is_admin")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # Allow if session is admin or admin password token provided
    admin_token = data.get("admin_password")
    if not is_admin and admin_token != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Admin authorization required.")

    action = data.get("action")  # 'start_timer', 'pause_timer', 'reset_timer', 'broadcast', 'clear_broadcast'
    conn = get_db_connection()
    cur = conn.cursor()
    now_ms = int(time.time() * 1000)

    if action == "start_timer":
        duration_m = float(data.get("duration_minutes", 20))
        duration_s = int(duration_m * 60)
        ends_at_ms = now_ms + (duration_s * 1000)
        title = data.get("title", f"ROUND {data.get('round_num', 1)}")
        round_num = str(data.get("round_num", 1))

        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_ends_at', ?)", (str(ends_at_ms),))
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_duration_s', ?)", (str(duration_s),))
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_running', 'true')")
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_title', ?)", (title,))
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_active_round', ?)", (round_num,))

        cur.execute("INSERT INTO events (kind, detail, ts_utc_ms) VALUES ('REMOTE_TIMER_START', ?, ?)",
                    (f"Flight Director started remote timer: {title} ({duration_m} min)", now_ms))

    elif action == "pause_timer":
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_running', 'false')")
        cur.execute("INSERT INTO events (kind, detail, ts_utc_ms) VALUES ('REMOTE_TIMER_PAUSE', 'Flight Director paused remote timer', ?)", (now_ms,))

    elif action == "reset_timer":
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_running', 'false')")
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_timer_ends_at', '0')")
        cur.execute("INSERT INTO events (kind, detail, ts_utc_ms) VALUES ('REMOTE_TIMER_RESET', 'Flight Director reset remote timer', ?)", (now_ms,))

    elif action == "broadcast":
        msg = data.get("message", "").strip()
        ann_id = str(now_ms)
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_announcement', ?)", (msg,))
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_announcement_id', ?)", (ann_id,))
        cur.execute("INSERT INTO events (kind, detail, ts_utc_ms) VALUES ('FLIGHT_BROADCAST', ?, ?)",
                    (f"Broadcast to all stations: {msg}", now_ms))

    elif action == "clear_broadcast":
        cur.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('competition_announcement', '')")

    conn.commit()
    conn.close()

    return {"status": "ok", "action": action, "timestamp_ms": now_ms}


@router.post("/api/auth/firebase_session")
async def create_firebase_session(request: Request):
    """
    Creates or links local session from Firebase Auth (Google or Anonymous).
    Ensures zero-friction entry for team workstations and team leads.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    uid = data.get("uid")
    email = data.get("email")
    display_name = data.get("displayName") or "Flight Crew"
    is_anon = data.get("isAnonymous", False)
    station_team_id = data.get("stationTeamId")

    if not uid:
        raise HTTPException(status_code=400, detail="Missing Firebase UID.")

    conn = get_db_connection()
    cur = conn.cursor()

    target_team = None

    # 1. If explicit station number provided
    if station_team_id:
        try:
            tid = int(station_team_id)
            if 1 <= tid <= TOTAL_TEAMS:
                cur.execute("SELECT * FROM teams WHERE id = ?", (tid,))
                target_team = cur.fetchone()
                
                # If team is not registered yet, auto-provision using master_answers.json
                if not target_team:
                    answers_file = os.path.join(ANSWERS_DIR, "master_answers.json")
                    if os.path.exists(answers_file):
                        with open(answers_file, "r", encoding="utf-8") as f:
                            master = json.load(f)
                        meta = master.get(str(tid))
                        if meta:
                            default_name = f"Station {tid} Flight Group"
                            pw_hash = hash_password(f"icarus_station_{tid}")
                            cur.execute("""
                            INSERT INTO teams (id, name, pw_hash, seed, credits, api_token, launch_auth_code, created_at)
                            VALUES (?, ?, ?, ?, 12, ?, ?, ?)
                            """, (tid, default_name, pw_hash, meta["seed"], meta["api_token"], meta["launch_auth_code"], datetime.now(timezone.utc).isoformat()))
                            conn.commit()
                            cur.execute("SELECT * FROM teams WHERE id = ?", (tid,))
                            target_team = cur.fetchone()
        except ValueError:
            pass

    # 2. If Google email provided, match existing registered teams
    if not target_team and email:
        # Check if email is associated with a team name or pattern
        cur.execute("SELECT * FROM teams WHERE name LIKE ?", (f"%{email.split('@')[0]}%",))
        target_team = cur.fetchone()

    # 3. Default fallback: assign Team 1 or first available team
    if not target_team:
        cur.execute("SELECT * FROM teams ORDER BY id ASC LIMIT 1")
        target_team = cur.fetchone()
        
    # If no team exists in database at all, auto-provision Team 1
    if not target_team:
        answers_file = os.path.join(ANSWERS_DIR, "master_answers.json")
        meta = {}
        if os.path.exists(answers_file):
            with open(answers_file, "r", encoding="utf-8") as f:
                master = json.load(f)
            meta = master.get("1", {})
        
        cur.execute("""
        INSERT INTO teams (id, name, pw_hash, seed, credits, api_token, launch_auth_code, created_at)
        VALUES (1, 'Station 1 Flight Group', ?, ?, 12, ?, ?, ?)
        """, (hash_password("icarus123"), meta.get("seed", "RVU_SEED_01"), meta.get("api_token", "RVU_TOKEN_01"), meta.get("launch_auth_code", "RVU-ORBIT-2027"), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        cur.execute("SELECT * FROM teams WHERE id = 1")
        target_team = cur.fetchone()

    conn.close()

    # Establish FastAPI session
    request.session["team_id"] = target_team["id"]
    request.session["team_name"] = target_team["name"]
    request.session["firebase_uid"] = uid
    request.session["firebase_email"] = email or "anonymous@station.icarus"
    request.session["auth_provider"] = "firebase_anon" if is_anon else "firebase_google"

    return {
        "status": "ok",
        "team_id": target_team["id"],
        "team_name": target_team["name"],
        "display_name": display_name,
        "is_anonymous": is_anon,
        "redirect": "/dashboard"
    }
