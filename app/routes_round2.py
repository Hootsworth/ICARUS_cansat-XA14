"""
Round 2 - Satellite Telemetry Investigation.

This router owns the participant-facing telemetry investigation without
changing the existing login, Round 1, Round 3, or global challenge APIs.
"""

import json
import os
import time
import csv
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from config import (
    TEAMS_DATA_DIR,
    ANSWERS_DIR,
    MISSION_EPOCH,
    MAX_ATTEMPTS_PER_CHALLENGE,
    COOLDOWN_DURATION_S,
    WRONG_ATTEMPT_PENALTY_PCT,
    MAX_TIME_BONUS_PCT,
    TIME_BONUS_DECAY_WINDOW_S,
    FIRST_SOLVER_BONUS_PCT,
    PASS_FRAME_COUNT,
    PASS_RATE_LIMIT_S,
    PASS_DEDUP_WINDOW_S,
    SERVER_ARCHIVES_DIR,
    FRAME_SIZE_BYTES,
    TOTAL_DURATION_S,
)
from models import get_db_connection
from app.routes_api import get_current_team_from_request, parse_iso_utc
from crypto_utils import generate_flag


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PHASE_2_CHALLENGES = [
    {
        "id": "C2.1",
        "title": "F1: Electrical Power Fault",
        "points": 200,
        "question": "Identify the exact UTC onset time of F1 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ EPS-07",
    },
    {
        "id": "C2.2",
        "title": "F2: Thermal Control Fault",
        "points": 200,
        "question": "Identify the exact UTC onset time of F2 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ THM-03",
    },
    {
        "id": "C2.3",
        "title": "F3: ADCS Cascade Fault",
        "points": 250,
        "question": "Identify the exact UTC onset time of F3 and its ICD fault code.",
        "format": "YYYY-MM-DDTHH:MM:SSZ ADCS-02",
    },
    {
        "id": "C2.4",
        "title": "F4: Communications Bit Error",
        "points": 200,
        "question": "Identify the corrupted frame ID and its ICD fault code.",
        "format": "reset_count:sequence COM-04",
    },
]

CHALLENGE_IDS = [c["id"] for c in PHASE_2_CHALLENGES]
CHALLENGE_MAP = {c["id"]: c for c in PHASE_2_CHALLENGES}


def _team_data_dir(team_id):
    return os.path.join(TEAMS_DATA_DIR, f"team_{int(team_id):02d}")


def _read_csv(filename, team_id):
    path = os.path.join(_team_data_dir(team_id), filename)

    if not os.path.exists(path):
        raise HTTPException(
            status_code=500,
            detail=f"Telemetry file not found: {filename}",
        )

    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_team_answers(team_id):
    path = os.path.join(ANSWERS_DIR, "master_answers.json")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=500,
            detail="Mission answer key is not available.",
        )

    with open(path, "r", encoding="utf-8") as f:
        answers = json.load(f)

    team_answers = answers.get(str(team_id))

    if not team_answers:
        raise HTTPException(
            status_code=500,
            detail="Team telemetry answer key is not available.",
        )

    return team_answers


def _round2_allowed(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT status FROM round_status WHERE team_id = ? AND round_id = 1",
        (team_id,),
    )
    r1 = cur.fetchone()

    cur.execute(
        "SELECT value FROM app_state WHERE key = 'round2_active'"
    )
    override = cur.fetchone()

    conn.close()

    r1_completed = bool(r1 and r1["status"] == "submitted")
    override_active = bool(
        override and str(override["value"]).lower() == "true"
    )

    return r1_completed or override_active


def _get_round2_state(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM round_status WHERE team_id = ? AND round_id = 2",
        (team_id,),
    )
    row = cur.fetchone()

    cur.execute(
        "SELECT value FROM app_state WHERE key = 'round2_active'"
    )
    override = cur.fetchone()

    conn.close()

    return {
        "status": row["status"] if row else "locked",
        "score": row["score"] if row else 0,
        "submitted_at": row["submitted_at"] if row else None,
        "active_override": bool(
            override and str(override["value"]).lower() == "true"
        ),
    }


def _get_challenge_rows(team_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT challenge_id, correct, points_awarded, attempt_no, ts_utc_ms
        FROM submissions
        WHERE team_id = ?
          AND challenge_id IN ('C2.1', 'C2.2', 'C2.3', 'C2.4')
        ORDER BY challenge_id, attempt_no
        """,
        (team_id,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def _evaluate_round2_answer(challenge_id, submitted_raw, expected):
    submitted = " ".join(str(submitted_raw).strip().split())
    answer = " ".join(str(expected.get("answer", "")).strip().split())
    alt = " ".join(str(expected.get("alt_answer", "")).strip().split())
    tolerance = float(expected.get("tolerance", 0))
    answer_type = expected.get("type", "string")

    if submitted.upper() == answer.upper():
        return True

    if alt and submitted.upper() == alt.upper():
        return True

    try:
        if answer_type == "iso_time_and_code":
            sub_parts = submitted.split()
            exp_parts = answer.split()

            if len(sub_parts) != 2 or len(exp_parts) != 2:
                return False

            sub_dt = parse_iso_utc(sub_parts[0])
            exp_dt = parse_iso_utc(exp_parts[0])

            return (
                abs((sub_dt - exp_dt).total_seconds()) <= tolerance
                and sub_parts[1].upper() == exp_parts[1].upper()
            )

        if answer_type == "frame_id_and_code":
            sub_parts = submitted.split()
            exp_parts = answer.split()

            if len(sub_parts) != 2 or len(exp_parts) != 2:
                return False

            return (
                sub_parts[0] == exp_parts[0]
                and sub_parts[1].upper() == exp_parts[1].upper()
            )

        if answer_type == "iso_time":
            sub_dt = parse_iso_utc(submitted)
            exp_dt = parse_iso_utc(answer)

            return abs((sub_dt - exp_dt).total_seconds()) <= tolerance

        if answer_type == "numeric":
            return abs(float(submitted) - float(answer)) <= tolerance

        if answer_type == "string":
            return submitted.upper() == answer.upper()

    except (ValueError, TypeError, OverflowError):
        return False

    return False


def _challenge_status(team_id):
    rows = _get_challenge_rows(team_id)

    result = {
        cid: {
            "solved": False,
            "points": 0,
            "attempts": 0,
            "remaining_attempts": MAX_ATTEMPTS_PER_CHALLENGE,
            "cooldown_remaining_s": 0,
        }
        for cid in CHALLENGE_IDS
    }

    now_ms = int(time.time() * 1000)

    for row in rows:
        cid = row["challenge_id"]

        if cid not in result:
            continue

        result[cid]["attempts"] += 1

        if row["correct"] == 1:
            result[cid]["solved"] = True
            result[cid]["points"] = row["points_awarded"]

        result[cid]["remaining_attempts"] = max(
            0,
            MAX_ATTEMPTS_PER_CHALLENGE - result[cid]["attempts"],
        )

    for cid in CHALLENGE_IDS:
        if result[cid]["solved"]:
            continue

        cid_rows = [r for r in rows if r["challenge_id"] == cid]

        if len(cid_rows) >= MAX_ATTEMPTS_PER_CHALLENGE:
            elapsed_s = (now_ms - cid_rows[-1]["ts_utc_ms"]) / 1000.0
            result[cid]["cooldown_remaining_s"] = max(
                0,
                int(COOLDOWN_DURATION_S - elapsed_s),
            )

    return result


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

    cur.execute("SELECT * FROM rounds WHERE id = 2")
    round_meta = cur.fetchone()

    conn.close()

    status = _challenge_status(team["id"])

    solved = {
        cid: item["points"]
        for cid, item in status.items()
        if item["solved"]
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
            "challenges": PHASE_2_CHALLENGES,
        },
    )


# ---------------------------------------------------------------------
# TEAM TELEMETRY
# ---------------------------------------------------------------------

@router.get("/api/round2/telemetry")
async def round2_telemetry(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if not _round2_allowed(team["id"]):
        raise HTTPException(status_code=403, detail="Round 2 is locked.")

    rows = _read_csv("beacon.csv", team["id"])

    return {
        "team_id": team["id"],
        "frame_count": len(rows),
        "telemetry": rows,
    }


# ---------------------------------------------------------------------
# PLANNED MISSION SCHEDULE
# ---------------------------------------------------------------------

@router.get("/api/round2/schedule")
async def round2_schedule(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if not _round2_allowed(team["id"]):
        raise HTTPException(status_code=403, detail="Round 2 is locked.")

    rows = _read_csv("planned_schedule.csv", team["id"])

    return {
        "team_id": team["id"],
        "events": rows,
    }


# ---------------------------------------------------------------------
# ROUND 2 STATUS
# ---------------------------------------------------------------------

@router.get("/api/round2/status")
async def round2_status(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return {
        "team_id": team["id"],
        "challenges": _challenge_status(team["id"]),
    }


# ---------------------------------------------------------------------
# ROUND 2 SUBMISSION
#
# Kept separate from /api/submit so this new Round 2 experience does not
# alter the existing global Round 4 challenge endpoint.
# ---------------------------------------------------------------------

@router.post("/api/round2/submit")
async def round2_submit(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if not _round2_allowed(team["id"]):
        raise HTTPException(status_code=403, detail="Round 2 is locked.")

    body = await request.json()

    challenge_id = str(body.get("challenge_id", "")).strip().upper()
    answer_raw = str(body.get("answer", "")).strip()

    if challenge_id not in CHALLENGE_MAP:
        raise HTTPException(status_code=404, detail="Round 2 challenge not found.")

    if not answer_raw:
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM submissions
        WHERE team_id = ?
          AND challenge_id = ?
        ORDER BY ts_utc_ms DESC
        """,
        (team["id"], challenge_id),
    )

    attempts = cur.fetchall()

    for row in attempts:
        if row["correct"] == 1:
            conn.close()
            return {
                "status": "already_solved",
                "message": f"{challenge_id} is already solved.",
                "points_awarded": row["points_awarded"],
            }

    now_ms = int(time.time() * 1000)
    attempt_count = len(attempts)

    if attempt_count >= MAX_ATTEMPTS_PER_CHALLENGE:
        elapsed_s = (now_ms - attempts[0]["ts_utc_ms"]) / 1000.0

        if elapsed_s < COOLDOWN_DURATION_S:
            remaining = int(COOLDOWN_DURATION_S - elapsed_s)
            conn.close()

            return JSONResponse(
                status_code=429,
                content={
                    "status": "cooldown",
                    "message": (
                        f"Maximum attempts reached. "
                        f"Try again in {remaining}s."
                    ),
                    "cooldown_remaining_s": remaining,
                },
            )

        attempt_count = 0

    team_answers = _load_team_answers(team["id"])
    expected = team_answers["challenges"].get(challenge_id)

    if not expected:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Answer key missing for {challenge_id}.",
        )

    correct = _evaluate_round2_answer(
        challenge_id,
        answer_raw,
        expected,
    )

    attempt_no = attempt_count + 1
    points_awarded = 0
    time_bonus = 0
    first_solver_bonus = 0

    if correct:
        base_points = CHALLENGE_MAP[challenge_id]["points"]

        penalty_factor = max(
            0.0,
            1.0 - (attempt_count * WRONG_ATTEMPT_PENALTY_PCT),
        )

        points_awarded = int(base_points * penalty_factor)

        elapsed_from_mission = max(
            0.0,
            (datetime.now(timezone.utc) - MISSION_EPOCH).total_seconds(),
        )

        decay_factor = max(
            0.0,
            1.0 - (
                elapsed_from_mission /
                TIME_BONUS_DECAY_WINDOW_S
            ),
        )

        time_bonus = int(
            base_points *
            MAX_TIME_BONUS_PCT *
            decay_factor
        )

        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM submissions
            WHERE challenge_id = ?
              AND correct = 1
            """,
            (challenge_id,),
        )

        first_solver = cur.fetchone()["count"] == 0

        if first_solver:
            first_solver_bonus = int(
                base_points * FIRST_SOLVER_BONUS_PCT
            )

        points_awarded += time_bonus + first_solver_bonus

    cur.execute(
        """
        INSERT INTO submissions
        (team_id, round_id, challenge_id, answer, correct,
         points_awarded, ts_utc_ms, attempt_no)
        VALUES (?, 4, ?, ?, ?, ?, ?, ?)
        """,
        (
            team["id"],
            challenge_id,
            answer_raw,
            1 if correct else 0,
            points_awarded,
            now_ms,
            attempt_no,
        ),
    )

    flag_unlocked = None

    if correct:
        solved_ids = {
            row["challenge_id"]
            for row in attempts
            if row["correct"] == 1
        }
        solved_ids.add(challenge_id)

        if all(cid in solved_ids for cid in CHALLENGE_IDS):
            flag_unlocked = team_answers["flags"].get("PHASE_2")

            if flag_unlocked:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO flags
                    (team_id, phase, flag, released_at)
                    VALUES (?, 'PHASE_2', ?, ?)
                    """,
                    (
                        team["id"],
                        flag_unlocked,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    conn.commit()
    conn.close()

    if correct:
        return {
            "status": "correct",
            "message": f"Correct! +{points_awarded} points.",
            "points_awarded": points_awarded,
            "time_bonus": time_bonus,
            "first_solver_bonus": first_solver_bonus,
            "flag_unlocked": flag_unlocked,
        }

    return JSONResponse(
        status_code=400,
        content={
            "status": "incorrect",
            "message": (
                f"Incorrect answer. "
                f"{max(0, MAX_ATTEMPTS_PER_CHALLENGE - attempt_no)} "
                f"attempts remaining."
            ),
            "remaining_attempts": max(
                0,
                MAX_ATTEMPTS_PER_CHALLENGE - attempt_no,
            ),
        },
    )


# ---------------------------------------------------------------------
# COMPLETE ROUND 2
# ---------------------------------------------------------------------

@router.post("/api/round2/complete")
async def complete_round2(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if not _round2_allowed(team["id"]):
        raise HTTPException(status_code=403, detail="Round 2 is locked.")

    conn = get_db_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in CHALLENGE_IDS)

    cur.execute(
        f"""
        SELECT challenge_id, MAX(points_awarded) AS points
        FROM submissions
        WHERE team_id = ?
          AND challenge_id IN ({placeholders})
          AND correct = 1
        GROUP BY challenge_id
        """,
        [team["id"], *CHALLENGE_IDS],
    )

    solved_rows = cur.fetchall()

    solved = {
        row["challenge_id"]: row["points"]
        for row in solved_rows
    }

    missing = [
        cid for cid in CHALLENGE_IDS
        if cid not in solved
    ]

    if missing:
        conn.close()

        return {
            "status": "incomplete",
            "missing": missing,
            "message": (
                "Solve all four telemetry investigations "
                "before completing Round 2."
            ),
        }

    total_score = sum(solved.values())
    now_iso = datetime.now(timezone.utc).isoformat()

    cur.execute(
        """
        INSERT OR REPLACE INTO round_status
        (team_id, round_id, status, score, unlocked_at, submitted_at)
        VALUES (
            ?, 2, 'submitted', ?,
            COALESCE(
                (
                    SELECT unlocked_at
                    FROM round_status
                    WHERE team_id = ? AND round_id = 2
                ),
                ?
            ),
            ?
        )
        """,
        (
            team["id"],
            total_score,
            team["id"],
            now_iso,
            now_iso,
        ),
    )

    # Preserve the existing Round 2 -> Round 3 progression behaviour.
    cur.execute(
        """
        INSERT OR REPLACE INTO round_status
        (team_id, round_id, status, score, unlocked_at)
        VALUES (?, 3, 'active', 0, ?)
        """,
        (team["id"], now_iso),
    )

    cur.execute(
        """
        INSERT INTO events (kind, detail, ts_utc_ms)
        VALUES (?, ?, ?)
        """,
        (
            "ROUND2_COMPLETED",
            (
                f"Team {team['id']} completed Telemetry Investigation "
                f"with {total_score} points."
            ),
            int(datetime.now(timezone.utc).timestamp() * 1000),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "status": "completed",
        "score": total_score,
        "solved": solved,
        "message": (
            f"Telemetry Investigation complete. "
            f"Score: {total_score} points."
        ),
    }


# ---------------------------------------------------------------------
# LEGACY COMPATIBILITY
# ---------------------------------------------------------------------

@router.get("/api/round2/dossiers")
async def legacy_round2_dossiers(request: Request):
    team = get_current_team_from_request(request)

    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return {
        "stations": [],
        "total_stations": 0,
        "message": (
            "Round 2 now uses the generated telemetry investigation."
        ),
    }
