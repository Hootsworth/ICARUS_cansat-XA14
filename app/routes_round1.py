"""
Round 1 — Mission Briefing & Physical Dossier Code Verification Engine.
"""
import os
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from models import get_db_connection
from app.routes_api import get_current_team_from_request

router = APIRouter()

@router.get("/api/round1/status")
async def round1_status(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, score, submitted_at FROM round_status WHERE team_id = ? AND round_id = 1", (team["id"],))
    row = cur.fetchone()
    conn.close()
    
    status = row["status"] if row else "active"
    score = row["score"] if row else 0
    submitted_at = row["submitted_at"] if row else None
    
    return {
        "team_id": team["id"],
        "status": status,
        "score": score,
        "submitted_at": submitted_at
    }


@router.post("/api/round1/submit")
async def round1_submit(request: Request):
    """
    Validates physical dossier launch authorization code submitted by the team.
    """
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")
        
    submitted_code = (data.get("code") or "").strip().upper()
    if not submitted_code:
        raise HTTPException(status_code=400, detail="Authorization code cannot be empty.")
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if already submitted
    cur.execute("SELECT status FROM round_status WHERE team_id = ? AND round_id = 1", (team["id"],))
    status_row = cur.fetchone()
    if status_row and status_row["status"] == "submitted":
        conn.close()
        return {
            "status": "already_submitted",
            "message": "Launch Authorisation Code has already been validated for your team."
        }
        
    # Check against team's expected launch_auth_code
    cur.execute("SELECT launch_auth_code FROM teams WHERE id = ?", (team["id"],))
    team_db = cur.fetchone()
    expected_code = (team_db["launch_auth_code"] or "").strip().upper()
    
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    if submitted_code == expected_code:
        # Success! Mark Round 1 as submitted with 100 points
        cur.execute("""
        INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at, submitted_at)
        VALUES (?, 1, 'submitted', 100, COALESCE((SELECT unlocked_at FROM round_status WHERE team_id = ? AND round_id = 1), ?), ?)
        """, (team["id"], team["id"], now_iso, now_iso))
        
        # Unlock Round 2 for this team
        cur.execute("""
        INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at)
        VALUES (?, 2, 'active', 0, ?)
        """, (team["id"], now_iso))
        
        # Log event
        cur.execute("""
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES ('ROUND1_VERIFIED', ?, ?)
        """, (f"Team {team['id']} ({team['name']}) successfully validated Launch Authorisation Code: {submitted_code}", now_ms))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": "Launch Authorisation Code accepted! Flight systems unlocked. Round 2 is now open.",
            "score": 100
        }
    else:
        # Invalid code
        cur.execute("""
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES ('ROUND1_FAILED_ATTEMPT', ?, ?)
        """, (f"Team {team['id']} ({team['name']}) attempted invalid Round 1 code: '{submitted_code}'", now_ms))
        conn.commit()
        conn.close()
        
        return {
            "status": "error",
            "message": "Invalid Launch Authorisation Code. Please re-verify your physical puzzle dossier and station sheets."
        }
