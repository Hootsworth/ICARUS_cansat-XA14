"""Round 2: CanSat telemetry anomaly investigation."""
import base64
import csv
import io
import os
import zipfile
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.routes_api import get_current_team_from_request
from models import get_db_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND2_DATA_DIR = os.environ.get("ROUND2_DATA_DIR", os.path.join(BASE_DIR, "round2_data"))
ROUND2_KEY = os.environ.get("ROUND2_DATA_KEY", "")
STAGE2_PASSWORD = os.environ.get("ROUND2_STAGE2_PASSWORD", "")
STAGE3_PASSWORD = os.environ.get("ROUND2_STAGE3_PASSWORD", "")
ANSWER_KEY_PATH = os.environ.get("ROUND2_ANSWER_KEY_PATH", os.path.join(ROUND2_DATA_DIR, "answer_key.b64"))

SUBSYSTEM_ALIASES = {
    "JITTER": {"telemetry", "telemetry link", "packet timing", "communications", "tt&c", "ttc"},
    "UNAUTH_CMD": {"command", "command and control", "c&c", "tt&c", "ttc", "camera", "cam"},
    "LINK_LOSS": {"telemetry", "telemetry link", "communications", "radio", "tt&c", "ttc"},
    "CAL_SHIFT": {"accelerometer", "imu", "attitude", "adcs"},
    "MAIN_LATE_INFLATE": {"parachute", "recovery", "main parachute", "recovery system"},
    "GPS_BARO_DECOUPLE": {"gps", "gnss", "barometer", "altitude", "navigation", "nav"},
    "LOG_MISMATCH": {"ground station", "groundstation", "rssi", "telemetry", "radio", "tt&c", "ttc"},
    "REPLAY": {"telemetry", "sensor", "data integrity", "packet integrity"},
    "MCU_RESET": {"mcu", "microcontroller", "obc", "avionics", "flight computer"},
    "STUCK_BIT": {"battery", "battery voltage", "vbat", "adc", "eps", "electrical power"},
    "SIG_MISMATCH": {"signature", "authentication", "integrity", "telemetry", "security"},
    "RTC_JUMP": {"rtc", "clock", "timekeeping", "timestamp"},
    "SENSOR_STUCK": {"temperature", "temperature sensor", "sensor", "thermal"},
    "STATE_VIOLATION": {"flight state", "state machine", "recovery", "parachute", "flight software"},
}


def ensure_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS round2_anomaly_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            submitted_timestamp TEXT NOT NULL,
            submitted_subsystem TEXT NOT NULL,
            description TEXT NOT NULL,
            matched_anomaly INTEGER,
            correct INTEGER NOT NULL,
            points_awarded INTEGER NOT NULL,
            ts_utc_ms INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)
    conn.commit()
    conn.close()


def _require_key():
    if not ROUND2_KEY:
        raise HTTPException(status_code=503, detail="Round 2 data key is not configured.")
    try:
        return base64.urlsafe_b64decode(ROUND2_KEY + "=" * (-len(ROUND2_KEY) % 4))
    except Exception:
        raise HTTPException(status_code=503, detail="Round 2 data key is invalid.")


def _decrypt_blob(path: str, aad: bytes) -> bytes:
    key = _require_key()
    try:
        with open(path, "rb") as f:
            packed = base64.b64decode(f.read())
        nonce, ciphertext = packed[:12], packed[12:]
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Round 2 dataset is not installed on the server.")
    except Exception:
        raise HTTPException(status_code=500, detail="Round 2 dataset could not be opened.")


def _load_team_package(team_id: int) -> zipfile.ZipFile:
    path = os.path.join(ROUND2_DATA_DIR, f"dataset_{team_id:02d}.b64")
    raw = _decrypt_blob(path, f"dataset_{team_id:02d}".encode())
    return zipfile.ZipFile(io.BytesIO(raw))


def _read_stage1(team_id: int, filename: str) -> str:
    with _load_team_package(team_id) as zf:
        try:
            return zf.read(f"stage1/{filename}").decode("utf-8")
        except KeyError:
            raise HTTPException(status_code=404, detail="Stage 1 file not found.")


def _read_locked_stage(team_id: int, stage: int) -> dict:
    password = STAGE2_PASSWORD if stage == 2 else STAGE3_PASSWORD
    if not password:
        raise HTTPException(status_code=503, detail=f"Stage {stage} password is not configured.")
    inner_name = f"stage{stage}_locked.zip"
    with _load_team_package(team_id) as outer:
        try:
            inner = outer.read(inner_name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Stage {stage} package not found.")
    try:
        with zipfile.ZipFile(io.BytesIO(inner)) as zf:
            names = zf.namelist()
            if not names:
                raise HTTPException(status_code=404, detail=f"Stage {stage} file is empty.")
            data = zf.read(names[0], pwd=password.encode())
            return {"filename": names[0], "content": data.decode("utf-8")}
    except RuntimeError:
        raise HTTPException(status_code=500, detail=f"Stage {stage} package password is incorrect.")


def _stage_active(stage: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_state WHERE key = ?", (f"round2_stage{stage}_active",))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["value"] == "true")


def _load_answers() -> list[dict]:
    raw = _decrypt_blob(ANSWER_KEY_PATH, b"answer_key_v2")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    for row in rows:
        row["n"] = int(row["n"])
    return rows


def _normalize_subsystem(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Timestamp must be ISO-8601 UTC, e.g. 2026-05-06T07:17:12.500Z")


@router.get("/round2", response_class=HTMLResponse)
async def round2_page(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        return RedirectResponse(url="/login", status_code=302)
    ensure_table()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rounds WHERE id = 2")
    r2_meta = cur.fetchone()
    cur.execute("SELECT * FROM round_status WHERE team_id = ? AND round_id = 1", (team["id"],))
    r1_status = cur.fetchone()
    cur.execute("SELECT value FROM app_state WHERE key = 'round2_active'")
    r2_override = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(points_awarded),0) AS score FROM round2_anomaly_submissions WHERE team_id = ?", (team["id"],))
    score_row = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS c FROM round2_anomaly_submissions WHERE team_id = ? AND correct = 1", (team["id"],))
    correct_count = cur.fetchone()["c"]
    conn.close()
    r1_completed = bool(r1_status and r1_status["status"] == "submitted")
    is_active = r1_completed or bool(r2_override and r2_override["value"] == "true")
    is_completed = correct_count >= 7
    return templates.TemplateResponse("round2.html", {
        "request": request,
        "team": team,
        "round_meta": r2_meta,
        "is_active": is_active,
        "is_completed": is_completed,
        "final_score": score_row["score"] if score_row else 0,
        "correct_count": correct_count,
        "stage2_active": _stage_active(2),
        "stage3_active": _stage_active(3),
    })


@router.get("/api/round2/stage1")
async def round2_stage1(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return {
        "mission_brief": _read_stage1(team["id"], "mission_brief.md"),
        "telemetry_csv": _read_stage1(team["id"], "telemetry.csv")
    }


@router.get("/api/round2/stage/{stage}")
async def round2_stage(request: Request, stage: int):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if stage not in (2, 3):
        raise HTTPException(status_code=404, detail="Invalid stage.")
    if not _stage_active(stage):
        raise HTTPException(status_code=403, detail=f"Stage {stage} has not been released yet.")
    return _read_locked_stage(team["id"], stage)


@router.get("/api/round2/submissions")
async def round2_my_submissions(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
    ensure_table()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, submitted_timestamp, submitted_subsystem, description, correct, points_awarded, ts_utc_ms "
        "FROM round2_anomaly_submissions WHERE team_id = ? ORDER BY id",
        (team["id"],)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"submissions": rows}


@router.post("/api/round2/submit-anomaly")
async def round2_submit_anomaly(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
    ensure_table()

    body = await request.json()
    timestamp_raw = str(body.get("timestamp", "")).strip()
    subsystem = str(body.get("subsystem", "")).strip()
    description = str(body.get("description", "")).strip()
    if not timestamp_raw or not subsystem or not description:
        raise HTTPException(status_code=400, detail="Timestamp, affected subsystem, and description are required.")

    submitted_dt = _parse_timestamp(timestamp_raw)
    subsystem_norm = _normalize_subsystem(subsystem)

    answers = [r for r in _load_answers() if r["dataset"] == f"dataset_{team['id']:02d}"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT matched_anomaly FROM round2_anomaly_submissions WHERE team_id = ? AND correct = 1",
        (team["id"],)
    )
    solved = {r["matched_anomaly"] for r in cur.fetchall() if r["matched_anomaly"] is not None}

    match = None
    for row in answers:
        if row["n"] in solved:
            continue
        expected_dt = _parse_timestamp(row["onset_utc"])
        time_ok = abs((submitted_dt - expected_dt).total_seconds()) <= 1.0
        subsystem_ok = any(alias in subsystem_norm for alias in SUBSYSTEM_ALIASES.get(row["type"], set()))
        if time_ok and subsystem_ok:
            match = row
            break

    correct = 1 if match else 0
    points = 10 if match else -5
    matched_n = match["n"] if match else None
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    cur.execute("""
        INSERT INTO round2_anomaly_submissions
        (team_id, submitted_timestamp, submitted_subsystem, description, matched_anomaly, correct, points_awarded, ts_utc_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (team["id"], timestamp_raw, subsystem, description, matched_n, correct, points, now_ms))

    cur.execute(
        "SELECT COALESCE(SUM(points_awarded),0) AS score FROM round2_anomaly_submissions WHERE team_id = ?",
        (team["id"],)
    )
    totals = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) AS c FROM round2_anomaly_submissions WHERE team_id = ? AND correct = 1",
        (team["id"],)
    )
    correct_total = cur.fetchone()["c"]
    complete = correct_total >= 7

    now_iso = datetime.now(timezone.utc).isoformat()
    if complete:
        cur.execute(
            "UPDATE round_status SET status='submitted', score=?, submitted_at=? WHERE team_id=? AND round_id=2",
            (totals["score"], now_iso, team["id"])
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO round_status (team_id, round_id, status, score, submitted_at) VALUES (?,2,'submitted',?,?)",
                (team["id"], totals["score"], now_iso)
            )
        cur.execute(
            "INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at) VALUES (?,3,'active',0,?)",
            (team["id"], now_iso)
        )
        cur.execute(
            "INSERT INTO events (kind, detail, ts_utc_ms) VALUES ('ROUND2_COMPLETED', ?, ?)",
            (f"Team {team['id']} completed Round 2 anomaly investigation", now_ms)
        )

    conn.commit()
    conn.close()

    return JSONResponse({
        "status": "correct" if match else "incorrect",
        "points_awarded": points,
        "score": totals["score"],
        "correct_count": correct_total,
        "completed": complete
    })


@router.post("/api/round2/focus-event")
async def round2_focus_event(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
    body = await request.json()
    kind = str(body.get("kind", "ROUND2_FOCUS_CHANGE"))[:80]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (kind, detail, ts_utc_ms) VALUES (?, ?, ?)",
        (kind, f"Team {team['id']} Round 2 page focus/visibility changed", now_ms)
    )
    conn.commit()
    conn.close()
    return {"ok": True}
