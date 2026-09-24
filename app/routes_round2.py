"""
Round 2 — Satellite Telemetry Investigation.
Team-specific, server-backed telemetry for the main ICARUS investigation round.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models import get_db_connection
from app.routes_api import get_current_team_from_request

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAIN_CHALLENGES = [
    "C1.1", "C1.2", "C1.3",
    "C2.1", "C2.2", "C2.3", "C2.4",
    "C3.1", "C3.2", "C3.3", "C3.4"
]
PHASE_COUNTS = {"PHASE_1": 3, "PHASE_2": 4, "PHASE_3": 4}

@router.get("/round2", response_class=HTMLResponse)
async def round2_page(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rounds WHERE id = 2")
    r2_meta = cur.fetchone()

    cur.execute("SELECT status, score, submitted_at FROM round_status WHERE team_id = ? AND round_id = 2", (team["id"],))
    status_row = cur.fetchone()

    cur.execute("SELECT status FROM round_status WHERE team_id = ? AND round_id = 1", (team["id"],))
    r1_status = cur.fetchone()
    r1_completed = bool(r1_status and r1_status["status"] == "submitted")

    cur.execute("SELECT value FROM app_state WHERE key = 'round2_active'")
    override = cur.fetchone()
    is_active = (override and override["value"] == "true") or r1_completed

    cur.execute("SELECT id, phase, title, points, description, order_num FROM challenges WHERE round_id = 2 ORDER BY order_num ASC")
    challenges = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT challenge_id, points_awarded FROM submissions WHERE team_id = ? AND round_id = 2 AND correct = 1", (team["id"],))
    solves = {row["challenge_id"]: row["points_awarded"] for row in cur.fetchall()}

    cur.execute("SELECT phase, flag FROM flags WHERE team_id = ?", (team["id"],))
    flags = {row["phase"]: row["flag"] for row in cur.fetchall()}

    conn.close()

    for ch in challenges:
        ch["is_solved"] = ch["id"] in solves
        ch["points_awarded"] = solves.get(ch["id"], 0)

    progress = {
        "PHASE_1": sum(1 for ch in challenges if ch["phase"] == "PHASE_1" and ch["is_solved"]),
        "PHASE_2": sum(1 for ch in challenges if ch["phase"] == "PHASE_2" and ch["is_solved"]),
        "PHASE_3": sum(1 for ch in challenges if ch["phase"] == "PHASE_3" and ch["is_solved"]),
        "BONUS": sum(1 for ch in challenges if ch["phase"] == "BONUS" and ch["is_solved"])
    }

    phase_data = {
        "PHASE_1": {
            "title": "Phase 1: Signal Acquisition",
            "desc": "Decode the raw dump. Establish the timing reference before touching the long-duration mission data."
        },
        "PHASE_2": {
            "title": "Phase 2: Downlink Investigation",
            "desc": "Use the beacon to decide where to spend scarce high-rate downlink credits. The archive contains decoys as well as real faults."
        },
        "PHASE_3": {
            "title": "Phase 3: Fault Isolation",
            "desc": "Reconstruct the failure chain, recover corrupted telemetry, and prove the physical meaning of the anomaly."
        },
        "BONUS": {
            "title": "Bonus Track: Uplink Forensics",
            "desc": "Audit the command log for authentication forgery and counter replay."
        }
    }

    is_completed = bool(status_row and status_row["status"] == "submitted")
    final_score = status_row["score"] if status_row else 0

    return templates.TemplateResponse("round2.html", {
        "request": request,
        "team": team,
        "round_meta": r2_meta,
        "is_active": is_active,
        "is_completed": is_completed,
        "final_score": final_score,
        "challenges": challenges,
        "solves": solves,
        "flags": flags,
        "progress": progress,
        "phase_data": phase_data,
        "phase_counts": PHASE_COUNTS,
        "main_challenge_count": len(MAIN_CHALLENGES),
        "main_solved": sum(1 for cid in MAIN_CHALLENGES if cid in solves)
    })


@router.get("/api/round2/status")
async def round2_status(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, score, submitted_at FROM round_status WHERE team_id = ? AND round_id = 2", (team["id"],))
    row = cur.fetchone()
    cur.execute("SELECT challenge_id FROM submissions WHERE team_id = ? AND round_id = 2 AND correct = 1", (team["id"],))
    solved = [r["challenge_id"] for r in cur.fetchall()]
    cur.execute("SELECT phase, flag FROM flags WHERE team_id = ?", (team["id"],))
    flags = {r["phase"]: r["flag"] for r in cur.fetchall()}
    conn.close()

    return {
        "team_id": team["id"],
        "status": row["status"] if row else "locked",
        "score": row["score"] if row else 0,
        "submitted_at": row["submitted_at"] if row else None,
        "solved": solved,
        "flags": flags
    }
