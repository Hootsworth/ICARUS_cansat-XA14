"""
Database layer and SQLite schema definitions.
"""
import sqlite3
import os
import json
from datetime import datetime, timezone
from config import DB_PATH, CHALLENGE_POINTS, DEFAULT_TEAM_CREDITS

def get_db_connection():
    """Returns a SQLite connection with dict-like row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and default tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Teams table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        seed INTEGER NOT NULL,
        credits INTEGER NOT NULL DEFAULT 12,
        api_token TEXT UNIQUE NOT NULL,
        launch_auth_code TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. Rounds table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- 'physical', 'quiz', 'game', 'code'
        description TEXT,
        opens_at TEXT NOT NULL,
        closes_at TEXT NOT NULL,
        prerequisite_round_id INTEGER,
        FOREIGN KEY (prerequisite_round_id) REFERENCES rounds(id)
    );
    """)

    # 3. Round Status per Team
    cur.execute("""
    CREATE TABLE IF NOT EXISTS round_status (
        team_id INTEGER NOT NULL,
        round_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'locked', -- 'locked', 'active', 'submitted'
        score INTEGER DEFAULT 0,
        unlocked_at TEXT,
        submitted_at TEXT,
        PRIMARY KEY (team_id, round_id),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );
    """)

    # 4. Quiz Questions Pool (Round 2)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT NOT NULL,
        options TEXT NOT NULL, -- JSON array of options
        correct_answer TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'medium',
        pool_tag TEXT NOT NULL DEFAULT 'general'
    );
    """)

    # 5. Quiz Active Sessions per Team (Server-Authoritative Timing)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        order_num INTEGER NOT NULL,
        started_at_ms INTEGER NOT NULL,
        time_limit_s INTEGER NOT NULL DEFAULT 25,
        status TEXT NOT NULL DEFAULT 'active', -- 'active', 'answered', 'expired'
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
    );
    """)

    # 6. Quiz Responses (Round 2)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        answer TEXT,
        is_correct INTEGER NOT NULL,
        time_taken_ms INTEGER NOT NULL,
        points_awarded INTEGER NOT NULL DEFAULT 0,
        server_timestamp TEXT NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
    );
    """)

    # 7. Game Sessions (Round 3 - Secret Scoring)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS game_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        round_id INTEGER NOT NULL DEFAULT 3,
        session_id TEXT UNIQUE NOT NULL,
        session_secret TEXT NOT NULL,
        signed_payload TEXT,
        raw_score INTEGER NOT NULL DEFAULT 0,
        verified INTEGER NOT NULL DEFAULT 0,
        started_at_ms INTEGER NOT NULL,
        submitted_at TEXT,
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );
    """)
    
    # 8. Challenges table (Round 4)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenges (
        id TEXT PRIMARY KEY,
        round_id INTEGER NOT NULL DEFAULT 4,
        phase TEXT NOT NULL,
        title TEXT NOT NULL,
        points INTEGER NOT NULL,
        tolerance_type TEXT NOT NULL,
        description TEXT NOT NULL,
        order_num INTEGER NOT NULL,
        FOREIGN KEY (round_id) REFERENCES rounds(id)
    );
    """)
    
    # 9. Submissions table (Round 4)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        round_id INTEGER NOT NULL DEFAULT 4,
        challenge_id TEXT NOT NULL,
        answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        points_awarded INTEGER NOT NULL DEFAULT 0,
        ts_utc_ms INTEGER NOT NULL,
        attempt_no INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (round_id) REFERENCES rounds(id),
        FOREIGN KEY (challenge_id) REFERENCES challenges(id)
    );
    """)
    
    # 10. Flags table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        phase TEXT NOT NULL,
        flag TEXT NOT NULL,
        released_at TEXT NOT NULL,
        UNIQUE(team_id, phase)
    );
    """)
    
    # 11. Downlink Passes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        start_utc TEXT NOT NULL,
        frames_count INTEGER NOT NULL DEFAULT 600,
        credits_charged INTEGER NOT NULL DEFAULT 1,
        ts_utc_ms INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id)
    );
    """)
    
    # 12. Console Log (Live Contingency Finale)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS console_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        cmd TEXT NOT NULL,
        sim_time_sec INTEGER NOT NULL,
        response TEXT NOT NULL,
        ts_utc_ms INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id)
    );
    """)
    
    # 13. Events & Announcements Log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        detail TEXT NOT NULL,
        ts_utc_ms INTEGER NOT NULL
    );
    """)
    
    # 14. Global State
    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    
    # Seed default rounds
    default_rounds = [
        (1, "Round 1: Mission Briefing", "physical", "Solve the offline physical cipher dossier to retrieve your launch authorization code.", "2027-03-14T00:00:00Z", "2027-03-14T23:59:59Z", None),
        (2, "Round 2: Rapid Flight Quiz", "quiz", "Server-authoritative timed rapid quiz testing telemetry, orbital dynamics, and avionics.", "2027-03-14T00:00:00Z", "2027-03-14T23:59:59Z", 1),
        (3, "Round 3: Mission Ops Mini-Game", "game", "Interactive CanSat/spacecraft resource management simulation across simulated orbits.", "2027-03-14T00:00:00Z", "2027-03-14T23:59:59Z", 2),
        (4, "Round 4: Telemetry Analysis", "code", "Forensic analysis of CanSat/satellite telemetry, anomaly isolation, and live recovery.", "2027-03-14T00:00:00Z", "2027-03-14T23:59:59Z", 3)
    ]
    for r in default_rounds:
        cur.execute("""
        INSERT OR IGNORE INTO rounds (id, name, type, description, opens_at, closes_at, prerequisite_round_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, r)

    # Populate Default Challenges for Round 4
    challenges_data = [
        ("C1.1", 4, "PHASE_1", "Clock Drift Calculation", CHALLENGE_POINTS["C1.1"], "numeric", "Determine OBC oscillator drift rate in PPM (or true dump start UTC).", 1),
        ("C1.2", 4, "PHASE_1", "Telemetry Gap Identification", CHALLENGE_POINTS["C1.2"], "iso_time_and_val", "Detect start UTC and duration (s) of missing frame gap in sample dump.", 2),
        ("C1.3", 4, "PHASE_1", "Tick Rollover Timestamp", CHALLENGE_POINTS["C1.3"], "iso_time", "Identify exact UTC timestamp of uint16 tick rollover (from 65535 to 0).", 3),
        
        ("C2.1", 4, "PHASE_2", "Fault 1: Electrical Power Subsystem", CHALLENGE_POINTS["C2.1"], "iso_time_and_code", "Identify F1 onset UTC and ICD signature code (e.g. 2027-03-14T... EPS-07).", 4),
        ("C2.2", 4, "PHASE_2", "Fault 2: Thermal Control Subsystem", CHALLENGE_POINTS["C2.2"], "iso_time_and_code", "Identify F2 unplanned heater onset UTC and ICD code.", 5),
        ("C2.3", 4, "PHASE_2", "Fault 3: ADCS Cascade Onset", CHALLENGE_POINTS["C2.3"], "iso_time_and_code", "Identify F3 cascade initial onset UTC and ICD code.", 6),
        ("C2.4", 4, "PHASE_2", "Fault 4: Communications Bit Error", CHALLENGE_POINTS["C2.4"], "frame_id_and_code", "Identify F4 single-bit corrupted frame ID (reset:seq) and ICD code.", 7),
        
        ("C3.1", 4, "PHASE_3", "Cascade Parameter Sequence", CHALLENGE_POINTS["C3.1"], "string", "Ordered list of parameter IDs whose deviation begins in F3 cascade.", 8),
        ("C3.2", 4, "PHASE_3", "OBC Reset Recovery Timestamp", CHALLENGE_POINTS["C3.2"], "iso_time", "UTC timestamp of the first frame transmitted after OBC reboot.", 9),
        ("C3.3", 4, "PHASE_3", "Bit Error Recovery & Voltage", CHALLENGE_POINTS["C3.3"], "index_and_mV", "0-based flipped bit index in frame and recovered original battery voltage (mV).", 10),
        ("C3.4", 4, "PHASE_3", "F1 Orbit & Post-Eclipse Voltage", CHALLENGE_POINTS["C3.4"], "orbit_and_mV", "Orbit index of F1 onset and battery voltage at end of that eclipse (mV).", 11),
        
        ("B1.1", 4, "BONUS", "Forged Uplink Telecommand", CHALLENGE_POINTS["B1.1"], "string", "Identify the command ID with forged HMAC signature in uplink_log.csv.", 12),
        ("B1.2", 4, "BONUS", "Replayed Uplink Telecommand", CHALLENGE_POINTS["B1.2"], "string", "Identify the command ID with replayed counter in uplink_log.csv.", 13),
        
        ("FINALE", 4, "FINALE", "Live Contingency Recovery", CHALLENGE_POINTS["FINALE"], "string", "Recover spacecraft from Safe Mode following flight runbook in live console.", 14),
    ]
    
    for c in challenges_data:
        cur.execute("""
        INSERT OR REPLACE INTO challenges (id, round_id, phase, title, points, tolerance_type, description, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, c)
        
    # Default App States
    defaults = {
        "competition_started": "true",
        "round1_active": "true",
        "round2_active": "true",
        "round3_active": "true",
        "round4_active": "true",
        "finale_started": "false",
        "scoreboard_frozen": "false",
        "errata_released": "false"
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO app_state (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()
