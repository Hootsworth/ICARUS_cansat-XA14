"""
Database migration script to upgrade existing RVSAT/ICARUS databases to the
Unified 4-Round Portal schema without losing any existing Round 4 challenges or submissions.
"""
import sqlite3
import os
import json
from config import DB_PATH

def migrate_db():
    print(f"[*] Starting migration for database: {DB_PATH}")
    db_exists = os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Ensure rounds table
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

    # 2. Ensure round_status table
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

    # 3. Ensure quiz_questions table
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

    # 4. Ensure quiz_sessions table
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

    # 5. Ensure quiz_responses table
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

    # 6. Ensure game_sessions table
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

    # 7. Add round_id column to challenges and submissions if not present
    if db_exists:
        cur.execute("PRAGMA table_info(challenges)")
        cols = [col[1] for col in cur.fetchall()]
        if cols and "round_id" not in cols:
            print("  -> Adding 'round_id' column to 'challenges' table...")
            cur.execute("ALTER TABLE challenges ADD COLUMN round_id INTEGER NOT NULL DEFAULT 4")

        cur.execute("PRAGMA table_info(submissions)")
        cols = [col[1] for col in cur.fetchall()]
        if cols and "round_id" not in cols:
            print("  -> Adding 'round_id' column to 'submissions' table...")
            cur.execute("ALTER TABLE submissions ADD COLUMN round_id INTEGER NOT NULL DEFAULT 4")

    # 8. Seed default rounds
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

    # 9. Seed default Quiz Question Pool (Round 2)
    cur.execute("SELECT COUNT(*) FROM quiz_questions")
    q_count = cur.fetchone()[0]
    if q_count == 0:
        print("  -> Seeding default question bank for Round 2...")
        questions = [
            # Trajectory & Aerodynamics
            ("At what flight phase does a CanSat transition from positive vertical velocity to negative vertical velocity?",
             json.dumps(["Apogee", "Ejection", "Terminal descent", "Booster cutoff"]),
             "Apogee", "easy", "trajectory"),
            ("Which sensor is primarily used to compute barometric altitude in a CanSat?",
             json.dumps(["BMP280 / Barometric Pressure Sensor", "3-axis Magnetometer", "Thermistor", "Optical encoder"]),
             "BMP280 / Barometric Pressure Sensor", "easy", "avionics"),
            ("What occurs if a CanSat's main recovery parachute fails to deploy at apogee?",
             json.dumps(["Descent rate exceeds safety limits (freefall/high impact)", "GPS signal lock increases", "Battery voltage spikes to 12V", "Telemetry frequency shifts"]),
             "Descent rate exceeds safety limits (freefall/high impact)", "easy", "recovery"),
            ("What mathematical formula relates atmospheric pressure P to barometric altitude h?",
             json.dumps(["Barometric Formula (Hypsometric equation)", "Kepler's Third Law", "Bernoulli's Venturi Law", "Stefan-Boltzmann Law"]),
             "Barometric Formula (Hypsometric equation)", "medium", "physics"),
            ("During steady unaccelerated parachute descent, what balances the downward gravitational force?",
             json.dumps(["Aerodynamic drag force", "Centripetal force", "Solar radiation pressure", "Magnetic torque"]),
             "Aerodynamic drag force", "easy", "physics"),

            # Avionics & Telemetry
            ("What is the primary function of an Attached Sync Marker (ASM) in a binary telemetry stream?",
             json.dumps(["Frame synchronization & byte alignment", "Data encryption", "Battery charging control", "OBC clock synchronization"]),
             "Frame synchronization & byte alignment", "medium", "telemetry"),
            ("In a Big-Endian 16-bit word, how is the value 0x1234 arranged in memory?",
             json.dumps(["Byte 0: 0x12, Byte 1: 0x34", "Byte 0: 0x34, Byte 1: 0x12", "Byte 0: 0x21, Byte 1: 0x43", "Byte 0: 0x43, Byte 1: 0x21"]),
             "Byte 0: 0x12, Byte 1: 0x34", "easy", "telemetry"),
            ("If a crystal oscillator has a drift of +25 PPM, by how many milliseconds will it drift in 1 hour?",
             json.dumps(["90 ms", "25 ms", "150 ms", "360 ms"]),
             "90 ms", "medium", "telemetry"),
            ("What does a CRC-16 checksum detect in a transmitted radio frame?",
             json.dumps(["Accidental single-bit or burst transmission errors", "Physical tampering by an adversary", "GPS satellite spoofing", "Processor watchdog timeouts"]),
             "Accidental single-bit or burst transmission errors", "easy", "telemetry"),
            ("Why is an IMU (accelerometer + gyroscope) sensor fusion filter (e.g. Madgwick or Kalman) needed for attitude determination?",
             json.dumps(["Gyros drift over time while accelerometers suffer from vibrational noise", "Gyros cannot measure angular rate", "Accelerometers only operate in vacuum", "IMUs do not have internal clocks"]),
             "Gyros drift over time while accelerometers suffer from vibrational noise", "medium", "avionics"),

            # Power & Thermal
            ("What is the typical nominal voltage of a single-cell Lithium Polymer (LiPo) battery under load?",
             json.dumps(["3.7 V", "1.2 V", "5.0 V", "9.0 V"]),
             "3.7 V", "easy", "power"),
            ("What causes a sharp voltage drop under heavy motor or heater load?",
             json.dumps(["Internal cell resistance (IR / IR drop)", "Increased ambient pressure", "Cosmic ray ionization", "Loss of ground RF lock"]),
             "Internal cell resistance (IR / IR drop)", "medium", "power"),
            ("In satellite thermal management, what is the primary mode of heat rejection in a vacuum?",
             json.dumps(["Thermal radiation", "Convection", "Conduction through air", "Evaporative cooling"]),
             "Thermal radiation", "easy", "thermal"),
            ("Why must CanSat battery packs be kept within thermal limits during high-altitude balloon flights?",
             json.dumps(["Cold temperatures drastically reduce available battery capacity and increase internal resistance", "Batteries ignite when sub-zero", "Voltage increases exponentially in cold", "GPS receivers refuse cold power"]),
             "Cold temperatures drastically reduce available battery capacity and increase internal resistance", "medium", "thermal"),

            # Orbital Dynamics & Space Operations
            ("What is the approximate orbital period of a Low Earth Orbit (LEO) satellite at 500 km altitude?",
             json.dumps(["~95 minutes", "~24 hours", "~45 minutes", "~12 hours"]),
             "~95 minutes", "easy", "orbit"),
            ("What is the term for the point in an orbit where a satellite is closest to Earth?",
             json.dumps(["Perigee", "Apogee", "Zenith", "Nadir"]),
             "Perigee", "easy", "orbit"),
            ("Which actuator is used on small satellites to dump angular momentum without consuming propellant?",
             json.dumps(["Magnetorquers (magnetic torque coils)", "Cold gas thrusters", "Solid rocket motors", "Solar sails"]),
             "Magnetorquers (magnetic torque coils)", "medium", "orbit"),
            ("What condition occurs when a satellite passes into the shadow cast by Earth?",
             json.dumps(["Orbital Eclipse (loss of solar power)", "Apogee blackout", "Solar conjunction", "Ionospheric scatter"]),
             "Orbital Eclipse (loss of solar power)", "easy", "orbit"),
            ("What is an SEU (Single Event Upset)?",
             json.dumps(["A radiation-induced state change in a memory cell or flip-flop", "A rocket separation failure", "A ground antenna misalignment", "A battery thermal runaway"]),
             "A radiation-induced state change in a memory cell or flip-flop", "medium", "avionics"),
            ("In cryptographic telecommand verification, what prevents replay attacks?",
             json.dumps(["A strictly incrementing sequence counter / nonce", "A static password", "CRC-16 checksum", "Baud rate modulation"]),
             "A strictly incrementing sequence counter / nonce", "medium", "security")
        ]

        for q in questions:
            cur.execute("""
            INSERT INTO quiz_questions (prompt, options, correct_answer, difficulty, pool_tag)
            VALUES (?, ?, ?, ?, ?)
            """, q)

    conn.commit()
    conn.close()
    print("[✓] Database migration completed successfully.")

if __name__ == "__main__":
    migrate_db()
