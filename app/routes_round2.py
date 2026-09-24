"""
Round 2 — Mission Go / No-Go: Flight Readiness Review Engine.
Interactive pre-flight engineering inspection dossiers testing real CanSat sensor systems.
"""
import time
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models import get_db_connection
from app.routes_api import get_current_team_from_request

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# The 5 Pre-Flight Inspection Stations & Engineering Solutions
READINESS_STATIONS = [
    {
        "id": 1,
        "subsystem": "ELECTRICAL POWER SUBSYSTEM (EPS)",
        "component": "2S LiPo Battery Pack & Power Distribution Board",
        "telemetry_data": {
            "Open Circuit Voltage": "8.38 V (Nominal)",
            "Loaded Voltage (2.5A Surge)": "6.12 V (Severe Sag)",
            "Pack Temperature": "-4.2 °C (Ambient Cold)",
            "Internal Resistance (IR)": "320 mΩ (Elevated 3x above nominal)",
            "Current Draw": "2.48 A"
        },
        "chart_label": "BATTERY VOLTAGE SAG UNDER TRANSIENT LOAD",
        "strip_chart": [
            "T-00:05 | 8.38V [======================]",
            "T-00:04 | 8.35V [===================== ]",
            "T-00:03 | 6.40V [================      ] LOAD APPLIED (2.5A)",
            "T-00:02 | 6.18V [==============        ]",
            "T-00:01 | 6.12V [=============         ] WARNING: REGULATOR DROPOUT MARGIN < 0.2V"
        ],
        "findings": "Pack temperature is sub-zero (-4.2°C). High internal cell resistance causes an acute 2.26V drop under RF transmission load, risking an OBC brownout during ascent.",
        "options": [
            {"id": "A", "text": "GO FOR FLIGHT: 6.12V is above the 5V bus regulator threshold."},
            {"id": "B", "text": "HOLD & CONDITION: Pre-warm battery pack to +15°C to restore internal resistance."},
            {"id": "C", "text": "NO-GO & SCRUB: LiPo cell chemistry permanently degraded, discard pack."},
            {"id": "D", "text": "GO WITH OVERRIDE: Disable radio telemetry during ascent to prevent current surge."}
        ],
        "correct_option": "B",
        "rationale": "Sub-zero battery temperature drastically elevates internal resistance. Conditioning and warming the pack to +15°C restores nominal IR (~90 mΩ) and eliminates inrush sag without replacing the pack."
    },
    {
        "id": 2,
        "subsystem": "RECOVERY & SEPARATION (REC)",
        "component": "Ejection Servo Mechanism & Deploy Door Interlock",
        "telemetry_data": {
            "Deploy Servo Current": "115 mA (Nominal)",
            "Door Microswitch Interlock": "CLOSED (Arm State)",
            "Servo Angle Range": "0° to 110° verified",
            "Release Pin Pull Force": "3.8 N (Spec: 3.5 to 5.0 N)",
            "Canopy Pack Pressure": "Nominal folded tension"
        },
        "chart_label": "SERVO ACTUATION PULSE & CURRENT PROFILE",
        "strip_chart": [
            "PULSE 1 | 112mA [====                  ] ANGLE: 0° (LATCHED)",
            "PULSE 2 | 118mA [=====                 ] SWEEP TEST",
            "PULSE 3 | 115mA [====                  ] ANGLE: 110° (RELEASED)",
            "PULSE 4 | 022mA [=                     ] RETURN TO DETENT",
            "STATUS  | INTERLOCK NOMINAL / RETENTION VERIFIED"
        ],
        "findings": "All servo actuation currents, release pin pull forces, and interlock microswitches match mechanical specifications exactly.",
        "options": [
            {"id": "A", "text": "HOLD: Re-pack parachute canopy with double talcum powder."},
            {"id": "B", "text": "NO-GO: Servo pull force of 3.8 N is too loose for rocket G-forces."},
            {"id": "C", "text": "GO FOR FLIGHT: Recovery mechanism actuation and retention within nominal margins."},
            {"id": "D", "text": "HOLD: Increase servo pulse width by 40% to guarantee ejection door blowout."}
        ],
        "correct_option": "C",
        "rationale": "Pull force of 3.8 N is precisely inside the 3.5–5.0 N specification window, and servo current is completely stable. All recovery parameters report nominal."
    },
    {
        "id": 3,
        "subsystem": "NAVIGATION & ATTITUDE (NAV)",
        "component": "GNSS L1 Receiver & Patch Antenna",
        "telemetry_data": {
            "Satellites Tracked": "4 SVs",
            "Fix Status": "2D Fix Only",
            "HDOP (Horiz Dilution)": "4.6 (Degraded)",
            "Altitude Estimate": "240 m ± 65 m (Unstable)",
            "Carrier-to-Noise (C/N0)": "28 dB-Hz (Fringe)"
        },
        "chart_label": "GNSS POSITION RESIDUAL ERRORS & SATELLITE LOCK",
        "strip_chart": [
            "EPOCH 1 | SVs: 3 | FIX: NONE | HDOP: 9.9",
            "EPOCH 2 | SVs: 4 | FIX: 2D   | HDOP: 5.8",
            "EPOCH 3 | SVs: 4 | FIX: 2D   | HDOP: 4.6 (MARGINAL)",
            "EPOCH 4 | ALTITUDE VARIANCE: ±65m JITTER",
            "STATUS  | INSUFFICIENT SATELLITE GEOMETRY FOR 3D TRAJECTORY"
        ],
        "findings": "The receiver only tracks 4 satellites with 2D fix and severe HDOP (4.6). Vertical altitude estimate has ±65m jitter, preventing reliable apogee and descent tracking.",
        "options": [
            {"id": "A", "text": "GO FOR FLIGHT: CanSat can rely exclusively on barometric altitude for apogee."},
            {"id": "B", "text": "HOLD: Reposition ground station test bench away from building obstruction to lock 3D fix (HDOP < 2.0)."},
            {"id": "C", "text": "NO-GO & SCRUB: Replace GNSS patch antenna with helical array."},
            {"id": "D", "text": "GO WITH OVERRIDE: Set GNSS baud rate from 9600 to 115200 bps."}
        ],
        "correct_option": "B",
        "rationale": "A 2D fix with 4 SVs is caused by local structural multipath/horizon masking on the pre-flight apron. Repositioning achieves a valid 3D fix with 7+ SVs (HDOP < 2.0) necessary for trajectory evaluation."
    },
    {
        "id": 4,
        "subsystem": "ATMOSPHERIC INSTRUMENTATION (PAYLOAD)",
        "component": "BMP280 Barometric Pressure & Temperature Sensor",
        "telemetry_data": {
            "Raw Pressure Reading": "1018.6 hPa",
            "Airfield QNH Reference": "1012.8 hPa (METAR)",
            "Derived Elevation": "-48.2 m (Sub-Surface Error)",
            "Sensor Temp": "22.4 °C",
            "I2C Bus Status": "ACK (Bus speed 100 kHz)"
        },
        "chart_label": "CALIBRATION RESIDUAL VS AIRFIELD GROUND TRUTH",
        "strip_chart": [
            "REF METAR | 1012.8 hPa | AIRFIELD ELEVATION: +12.0m AMSL",
            "SENSOR    | 1018.6 hPa | COMPUTED: -48.2m AMSL",
            "RESIDUAL  | +5.8 hPa OFFSET ERROR",
            "IMPACT    | APOGEE & DESCENT RATE CALCULATIONS SYSTEMATICALLY BIASED",
            "STATUS    | ZERO-POINT HYPSOMETRIC BIAS DETECTED"
        ],
        "findings": "The barometer has a static +5.8 hPa bias compared to official airfield QNH, causing the CanSat to believe it is 48 meters below sea level.",
        "options": [
            {"id": "A", "text": "GO FOR FLIGHT: Altitude offsets cancel out when computing vertical descent velocity."},
            {"id": "B", "text": "NO-GO: Discard BMP280 sensor; sensor element membrane ruptured."},
            {"id": "C", "text": "CALIBRATE & GO: Apply +5.8 hPa ground reference compensation to flight computer software."},
            {"id": "D", "text": "HOLD: Submerge CanSat in hermetic chamber to reset factory firmware."}
        ],
        "correct_option": "C",
        "rationale": "Barometric pressure sensors require ground-level baseline zeroing against official QNH. Offsetting the reference pressure calibrates the altitude zero-mark with zero hardware changes."
    },
    {
        "id": 5,
        "subsystem": "TELEMETRY & COMMAND (TT&C)",
        "component": "LoRa 433 MHz Radio Transceiver & Ground Link",
        "telemetry_data": {
            "Tx Power": "20 dBm (100 mW)",
            "Antenna VSWR": "1.18 : 1 (Excellent match)",
            "Ground RSSI (100m Line of Sight)": "-48 dBm (Strong)",
            "Packet Error Rate (PER)": "0.0 % (100/100 Packets)",
            "Center Frequency Offset": "+1.2 kHz (Within AFC tolerance)"
        },
        "chart_label": "RF SPECTRUM PURITY & PACKET LINK MARGIN",
        "strip_chart": [
            "LINK TEST | 100 PACKETS TRANSMITTED | 100 ACK RECEIVED",
            "RSSI      | -48 dBm [======================] MARGIN: +72 dB",
            "SNR       | +10.5 dB (EXCELLENT SPREADING)",
            "VSWR      | 1.18 : 1 (REFLECTED POWER < 0.6%)",
            "STATUS    | FLIGHT RADIO LINK FULLY CERTIFIED"
        ],
        "findings": "All radio metrics (VSWR, packet delivery, SNR margin, frequency stability) meet flight ground station criteria.",
        "options": [
            {"id": "A", "text": "GO FOR FLIGHT: RF link budget and antenna matching fully certified."},
            {"id": "B", "text": "HOLD: Increase transmission power to 30 dBm (1W) for extra safety margin."},
            {"id": "C", "text": "HOLD: Trim antenna length by 5mm to achieve 1.00 VSWR."},
            {"id": "D", "text": "NO-GO: Frequency offset of +1.2 kHz exceeds civilian radio regulations."}
        ],
        "correct_option": "A",
        "rationale": "A VSWR of 1.18:1 reflects less than 0.6% power, packet error rate is 0.0%, and link margin is +72 dB. Pushing to 30 dBm is illegal and drains battery. The radio is ready for flight."
    }
]

# -----------------------------------------------------------------------------
# HTML PAGE CONTROLLER
# -----------------------------------------------------------------------------
@router.get("/round2", response_class=HTMLResponse)
async def round2_page(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        return RedirectResponse(url="/login", status_code=302)
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM rounds WHERE id = 2")
    r2_meta = cur.fetchone()
    
    cur.execute("SELECT * FROM round_status WHERE team_id = ? AND round_id = 2", (team["id"],))
    status_row = cur.fetchone()
    
    cur.execute("SELECT * FROM round_status WHERE team_id = ? AND round_id = 1", (team["id"],))
    r1_status = cur.fetchone()
    r1_completed = bool(r1_status and r1_status["status"] == "submitted")
    
    cur.execute("SELECT value FROM app_state WHERE key = 'round2_active'")
    r2_override = cur.fetchone()
    is_active = (r2_override and r2_override["value"] == "true") or r1_completed
    
    conn.close()
    
    is_completed = bool(status_row and status_row["status"] == "submitted")
    final_score = status_row["score"] if (status_row and is_completed) else 0
    
    return templates.TemplateResponse("round2.html", {
        "request": request,
        "team": team,
        "round_meta": r2_meta,
        "is_active": is_active,
        "is_completed": is_completed,
        "final_score": final_score
    })


# -----------------------------------------------------------------------------
# API CONTROLLERS
# -----------------------------------------------------------------------------
@router.get("/api/round2/dossiers")
async def round2_get_dossiers(request: Request):
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    # Return sanitized stations without revealing correct answers
    sanitized = []
    for s in READINESS_STATIONS:
        sanitized.append({
            "id": s["id"],
            "subsystem": s["subsystem"],
            "component": s["component"],
            "telemetry_data": s["telemetry_data"],
            "chart_label": s["chart_label"],
            "strip_chart": s["strip_chart"],
            "findings": s["findings"],
            "options": s["options"]
        })
    return {"stations": sanitized, "total_stations": len(sanitized)}


@router.post("/api/round2/evaluate")
async def round2_evaluate_calls(request: Request):
    """
    Submits flight calls for all 5 stations.
    Awards 100 points per correct engineering decision (up to 500 points).
    """
    team = get_current_team_from_request(request)
    if not team:
        raise HTTPException(status_code=401, detail="Authentication required.")
        
    try:
        body = await request.json()
        calls = body.get("calls", {}) # { "1": "B", "2": "C", ... }
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload format.")
        
    total_score = 0
    results = {}
    
    for s in READINESS_STATIONS:
        sid = str(s["id"])
        submitted_call = (calls.get(sid) or "").strip().upper()
        correct_call = s["correct_option"]
        is_correct = (submitted_call == correct_call)
        
        if is_correct:
            total_score += 100
            
        results[sid] = {
            "subsystem": s["subsystem"],
            "is_correct": is_correct,
            "submitted": submitted_call,
            "correct": correct_call,
            "rationale": s["rationale"],
            "points": 100 if is_correct else 0
        }
        
    # Update round_status
    conn = get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    cur.execute("""
    INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, submitted_at)
    VALUES (?, 2, 'submitted', ?, ?)
    """, (team["id"], total_score, now_iso))
    
    # Auto-unlock Round 3
    cur.execute("""
    INSERT OR REPLACE INTO round_status (team_id, round_id, status, score, unlocked_at)
    VALUES (?, 3, 'active', 0, ?)
    """, (team["id"], now_iso))
    
    cur.execute("""
    INSERT INTO events (kind, detail, ts_utc_ms)
    VALUES ('ROUND2_COMPLETED', ?, ?)
    """, (f"Team {team['id']} completed Flight Readiness Review with {total_score}/500 PTS", now_ms))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "completed",
        "total_score": total_score,
        "results": results,
        "message": f"Flight Readiness Review logged. Station score: {total_score} PTS."
    }
