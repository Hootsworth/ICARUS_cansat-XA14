"""
Round 2 - Satellite Telemetry Investigation.
Loads team-specific generated telemetry and exposes the Phase 2 investigation APIs.
"""

import csv
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import TEAMS_DATA_DIR
from models import get_db_connection
from app.routes_api import get_current_team_from_request


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PHASE_2_CHALLENGES = [
    {
        "id": "C2.1",
        "title": "F1: Electrical Power Fault",
        "points": 200,
        "question": "Identify the exact UTC onset time of F1 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ EPS-07"
    },
    {
        "id": "C2.2",
        "title": "F2: Thermal Control Fault",
        "points": 200,
        "question": "Identify the exact UTC onset time of F2 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ THM-03"
    },
    {
        "id": "C2.3",
        "title": "F3: ADCS Cascade Fault",
        "points": 250,
        "question": "Identify the exact UTC onset time of F3 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ ADCS-02"
    },
    {
        "id": "C2.4",
        "title": "F4: Communications Bit Error",
        "points": 200,
        "question": "Identify the corrupted frame ID and its ICD fault code.",
        "format": "reset_count:sequence COM-04"
    }
]


def _team_data_dir(team_id):
    return os.path.join(TEAMS_DATA_DIR, f"team_{int(team_id):02d}")


def _read_csv(filename, team_id):
    path = os.path.join(_team_data_dir(team_id), filename)

    if not os.path.exists(path):
        raise HTTPException(
            status_code=500,
            detail=f"Telemetry file not found: {filename}"
        )

    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _get_round2_state(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM round_status WHERE team_id = ? AND round_id = 2",
        (team_id,)
    )
    row = cur.fetchone()

    cur.execute(
        "SELECT value FROM app_state WHERE key = 'round2_active'"
    )
    override = cur.fetchone()

    conn.close()

    active_override = bool(
        override and override["value"].lower() == "true"
    )

    return {
        "status": row["status"] if row else "locked",
        "score": row["score"] if row else 0,
        "submitted_at": row["submitted_at"] if row else None,
        "active_override": active_override
    }


def _round2_allowed(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT status FROM round_status WHERE team_id = ? AND round_id = 1",
        (team_id,)
    )
    r1 = cur.fetchone()

    cur.execute(
        "SELECT value FROM app_state WHERE key = 'round2_active'"
    )
    override = cur.fetchone()

    conn.close()

    r1_completed = bool(r1 and r1["status"] == "submitted")
    override_active = bool(
        override and override["value"].lower() == "true"
    )

    return r1_completed or override_active


# ---------------------------------------------------------------------
# ROUND 2 PAGE
# ---------------------------------------------------------------------

@router.get("/round2", response_class=HTMLResponse)
async def round2_page(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        return RedirectResponse(url="/login", status_code=302)

    state = _get_round2_state(team["id"])
    allowed = _round2_allowed(team["id"])

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM rounds WHERE id = 2"
    )
    round_meta = cur.fetchone()

    cur.execute(
        """
        SELECT challenge_id, MAX(points_awarded) AS points
        FROM submissions
        WHERE team_id = ?
          AND challenge_id IN ('C2.1', 'C2.2', 'C2.3', 'C2.4')
          AND correct = 1
        GROUP BY challenge_id
        """,
        (team["id"],)
    )

    solved_rows = cur.fetchall()
    conn.close()

    solved = {
        row["challenge_id"]: row["points"]
        for row in solved_rows
    }

    return templates.TemplateResponse(
        "round2.html",
        {
            "request": request,
            "team": team,
            "round_meta": round_meta,
            "is_active": allowed,
            "is_completed": state["status"] == "submitted",
            "final_score": state["score"],
            "solved": solved,
            "challenges": PHASE_2_CHALLENGES
        }
    )


# ---------------------------------------------------------------------
# TEAM TELEMETRY
# ---------------------------------------------------------------------

@router.get("/api/round2/telemetry")
async def round2_telemetry(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if not _round2_allowed(team["id"]):
        raise HTTPException(
            status_code=403,
            detail="Round 2 is locked."
        )

    rows = _read_csv("beacon.csv", team["id"])

    return {
        "team_id": team["id"],
        "frame_count": len(rows),
        "telemetry": rows
    }


# ---------------------------------------------------------------------
# PLANNED MISSION SCHEDULE
# ---------------------------------------------------------------------

@router.get("/api/round2/schedule")
async def round2_schedule(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if not _round2_allowed(team["id"]):
        raise HTTPException(
            status_code=403,
            detail="Round 2 is locked."
        )

    rows = _read_csv("planned_schedule.csv", team["id"])

    return {
        "team_id": team["id"],
        "events": rows
    }


# ---------------------------------------------------------------------
# ROUND 2 CHALLENGE STATUS
# ---------------------------------------------------------------------

@router.get("/api/round2/status")
async def round2_status(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT challenge_id, correct, points_awarded, attempt_no
        FROM submissions
        WHERE team_id = ?
          AND challenge_id IN ('C2.1', 'C2.2', 'C2.3', 'C2.4')
        ORDER BY challenge_id, attempt_no
        """,
        (team["id"],)
    )

    rows = cur.fetchall()
    conn.close()

    challenges = {}

    for row in rows:
        cid = row["challenge_id"]

        if cid not in challenges:
            challenges[cid] = {
                "solved": False,
                "points": 0,
                "attempts": 0
            }

        challenges[cid]["attempts"] += 1

        if row["correct"] == 1:
            challenges[cid]["solved"] = True
            challenges[cid]["points"] = row["points_awarded"]

    return {
        "team_id": team["id"],
        "challenges": challenges
    }


# ---------------------------------------------------------------------
# COMPLETE ROUND 2
# ---------------------------------------------------------------------

@router.post("/api/round2/complete")
async def complete_round2(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    challenge_ids = ["C2.1", "C2.2", "C2.3", "C2.4"]

    conn = get_db_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in challenge_ids)

    cur.execute(
        f"""
        SELECT challenge_id, MAX(points_awarded) AS points
        FROM submissions
        WHERE team_id = ?
          AND challenge_id IN ({placeholders})
          AND correct = 1
        GROUP BY challenge_id
        """,
        [team["id"], *challenge_ids]
    )

    solved_rows = cur.fetchall()

    solved = {
        row["challenge_id"]: row["points"]
        for row in solved_rows
    }

    missing = [
        cid for cid in challenge_ids
        if cid not in solved
    ]

    if missing:
        conn.close()

        return {
            "status": "incomplete",
            "missing": missing,
            "message": "Solve all four Phase 2 investigations before completing Round 2."
        }

    total_score = sum(solved.values())
    now_iso = datetime.now(timezone.utc).isoformat()

    cur.execute(
        """
        INSERT OR REPLACE INTO round_status
        (team_id, round_id, status, score, unlocked_at, submitted_at)
        VALUES (?, 2, 'submitted', ?, 
                COALESCE(
                    (SELECT unlocked_at FROM round_status
                     WHERE team_id = ? AND round_id = 2),
                    ?
                ),
                ?)
        """,
        (
            team["id"],
            total_score,
            team["id"],
            now_iso,
            now_iso
        )
    )

    # Unlock Round 3 after successful Round 2 completion.
    cur.execute(
        """
        INSERT OR REPLACE INTO round_status
        (team_id, round_id, status, score, unlocked_at)
        VALUES (?, 3, 'active', 0, ?)
        """,
        (team["id"], now_iso)
    )

    cur.execute(
        """
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES (?, ?, ?)
        """,
        (
            "ROUND2_COMPLETED",
            f"Team {team['id']} completed Telemetry Investigation with {total_score} points.",
            int(datetime.now(timezone.utc).timestamp() * 1000)
        )
    )

    conn.commit()
    conn.close()

    return {
        "status": "completed",
        "score": total_score,
        "solved": solved,
        "message": f"Telemetry Investigation complete. Score: {total_score} points."
    }


# ---------------------------------------------------------------------
# COMPATIBILITY ENDPOINT
# ---------------------------------------------------------------------

@router.get("/api/round2/dossiers")
async def legacy_round2_dossiers(request: Request):
    """
    Kept so older frontend code does not crash.
    The real telemetry endpoint is /api/round2/telemetry.
    """

    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    return {
        "stations": [],
        "total_stations": 0,
        "message": "Round 2 now uses the generated telemetry investigation."
    }
