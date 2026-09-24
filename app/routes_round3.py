"""
Round 3 — Mission Ops Mini-Game Route Controllers & Signed-Score Verification Engine.
CRITICAL: Round 3 raw scores are strictly secret and must NEVER be exposed in any team-facing responses.
"""
import time
import json
import uuid
import hmac
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import MASTER_SECRET
from models import get_db_connection
from app.routes_api import get_current_team_from_request
from crypto_utils import generate_game_session_secret, compute_game_hmac

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MIN_GAMEPLAY_DURATION_MS = 15000   # Minimum 15s of gameplay required for atmospheric drop
MAX_THEORETICAL_SCORE = 500       # Maximum bound for scoring sanity
INITIAL_ALTITUDE_M = 1000

# -----------------------------------------------------------------------------
# HTML PAGE CONTROLLER
# -----------------------------------------------------------------------------
@router.get("/round3", response_class=HTMLResponse)
async def round3_page(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        return RedirectResponse(url="/login", status_code=302)
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if Round 3 is unlocked
    cur.execute("SELECT * FROM rounds WHERE id = 3")
    r3_meta = cur.fetchone()
    
    cur.execute("SELECT * FROM round_status WHERE team_id = ? AND round_id = 3", (team["id"],))
    status_row = cur.fetchone()
    
    # Check prerequisite (Round 2)
    cur.execute("SELECT * FROM round_status WHERE team_id = ? AND round_id = 2", (team["id"],))
    r2_status = cur.fetchone()
    r2_completed = bool(r2_status and r2_status["status"] == "submitted")
    
    # Admin override check
    cur.execute("SELECT value FROM app_state WHERE key = 'round3_active'")
    r3_override = cur.fetchone()
    is_active = (r3_override and r3_override["value"] == "true") or r2_completed
    
    conn.close()
    
    is_completed = bool(status_row and status_row["status"] == "submitted")
    
    # NOTE: We deliberately do NOT pass raw_score to the template!
    return templates.TemplateResponse("round3.html", {
        "request": request,
        "team": team,
        "round_meta": r3_meta,
        "is_active": is_active,
        "is_completed": is_completed
    })


# -----------------------------------------------------------------------------
# API CONTROLLERS
# -----------------------------------------------------------------------------
@router.get("/api/round3/status")
async def round3_api_status(request: Request):
    """
    Returns team status for Round 3.
    NEVER returns raw score to teams.
    """
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, submitted_at FROM round_status WHERE team_id = ? AND round_id = 3", (team["id"],))
    row = cur.fetchone()
    conn.close()
    
    status = row["status"] if row else "locked"
    return {
        "team_id": team["id"],
        "status": status,
        "submitted_at": row["submitted_at"] if row else None
    }


@router.post("/api/round3/session/start")
async def round3_session_start(request: Request):
    """
    Issues a cryptographically signed session token for the interactive canvas game.
    """
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if team already completed Round 3
    cur.execute("SELECT status FROM round_status WHERE team_id = ? AND round_id = 3", (team["id"],))
    status_row = cur.fetchone()
    if status_row and status_row["status"] == "submitted":
        conn.close()
        raise HTTPException(status_code=400, detail="Round 3 has already been completed and submitted.")
        
    now_ms = int(time.time() * 1000)
    session_id = f"r3_{team['id']}_{uuid.uuid4().hex[:12]}"
    session_secret = generate_game_session_secret(MASTER_SECRET, team["id"], session_id, now_ms)
    
    # Store session in DB
    cur.execute("""
    INSERT INTO game_sessions (team_id, round_id, session_id, session_secret, raw_score, verified, started_at_ms)
    VALUES (?, 3, ?, ?, 0, 0, ?)
    """, (team["id"], session_id, session_secret, now_ms))
    
    cur.execute("""
    INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at)
    VALUES (?, 3, 'active', 0, ?)
    """, (team["id"], datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "ready",
        "session_id": session_id,
        "session_token": session_secret,
        "altitude_m": INITIAL_ALTITUDE_M,
        "message": "Atmospheric CanSat ejection armed. Good luck, Flight Controller."
    }


@router.post("/api/round3/submit")
async def round3_submit_score(request: Request):
    """
    Verifies HMAC cryptographic signature and sanity bounds before accepting Round 3 score.
    Zero-leakage guarantee: Does NOT return the raw score in the response.
    """
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")
        
    session_id = data.get("session_id")
    raw_score = data.get("raw_score")
    p1 = data.get("p1", data.get("survived_orbits", 0))
    p2 = data.get("p2", data.get("actions_count", 0))
    signature = data.get("signature", "")
    metrics = data.get("metrics", {})
    
    if not session_id or raw_score is None or not signature:
        raise HTTPException(status_code=400, detail="Missing required telemetry payload or cryptographic signature.")
        
    now_ms = int(time.time() * 1000)
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch session
    cur.execute("SELECT * FROM game_sessions WHERE session_id = ? AND team_id = ?", (session_id, team["id"]))
    session = cur.fetchone()
    
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Invalid or non-existent game session.")
        
    if session["verified"] == 1:
        conn.close()
        raise HTTPException(status_code=400, detail="Game session has already been finalized.")
        
    session_secret = session["session_secret"]
    
    # 1. Cryptographic HMAC Verification
    expected_hmac = compute_game_hmac(session_secret, session_id, int(raw_score), int(p1), int(p2))
    if not hmac.compare_digest(expected_hmac.lower(), signature.lower()):
        cur.execute("""
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES ('SECURITY_ALERT', ?, ?)
        """, (f"Team {team['id']} submitted invalid HMAC signature for Round 3 session {session_id}", now_ms))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail="Cryptographic signature verification failed. Telemetry rejected.")
        
    # 2. Timing Sanity Check (Prevent bot instantaneous POSTs)
    elapsed_ms = now_ms - session["started_at_ms"]
    if elapsed_ms < MIN_GAMEPLAY_DURATION_MS:
        cur.execute("""
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES ('SECURITY_ALERT', ?, ?)
        """, (f"Team {team['id']} submitted Round 3 unrealistically fast ({elapsed_ms}ms)", now_ms))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=400, detail="Flight drop duration is below physical atmospheric descent threshold.")
        
    # 3. Score Upper/Lower Bound Check
    int_score = max(0, min(MAX_THEORETICAL_SCORE, int(raw_score)))
    
    # 4. Record Verified Session and Update Round Status
    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    UPDATE game_sessions 
    SET raw_score = ?, signed_payload = ?, verified = 1, submitted_at = ?
    WHERE session_id = ?
    """, (int_score, json.dumps(data), now_iso, session_id))
    
    cur.execute("""
    UPDATE round_status 
    SET status = 'submitted', score = ?, submitted_at = ?
    WHERE team_id = ? AND round_id = 3
    """, (int_score, now_iso, team["id"]))
    
    conn.commit()
    conn.close()
    
    # Response strictly omits raw_score
    return {
        "status": "verified",
        "verified": True,
        "message": "CanSat atmospheric flight telemetry authenticated and archived into official flight ledger."
    }

