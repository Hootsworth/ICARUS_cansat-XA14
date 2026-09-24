"""
Configuration constants, competition timing, scoring parameters, and mission defaults.
"""
import os
from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# Mission Identity & Theming
# -----------------------------------------------------------------------------
MISSION_NAME = "RVSAT-1"
ORGANIZATION_NAME = "RV University"
EVENT_TITLE = "Satellite Telemetry & Flight Operations Challenge"
EVENT_JOIN_CODE = "RVU-ORBIT-2027"

# Master Secret used for HMAC key derivation and flag generation
MASTER_SECRET = os.environ.get("RVSAT_MASTER_SECRET", "RVU_TELEMETRY_MASTER_SECRET_KEY_98471")
ADMIN_PASSWORD = os.environ.get("RVSAT_ADMIN_PASSWORD", "rvu_flight_ops_admin_2027")

# Total Teams in competition
TOTAL_TEAMS = 11

# -----------------------------------------------------------------------------
# Spacecraft Orbit & Telemetry Simulation Parameters
# -----------------------------------------------------------------------------
ORBIT_PERIOD_S = 5700       # 95 minutes
SUNLIT_DURATION_S = 3600    # 60 minutes
ECLIPSE_DURATION_S = 2100   # 35 minutes
TOTAL_DURATION_S = 86400    # 24 hours (86,400 seconds = 86,400 frames)

# Frame constants
FRAME_SIZE_BYTES = 44
ASM_BYTES = bytes([0x1A, 0xCF, 0xFC, 0xE1])  # 0x1ACFFCE1
SPACECRAFT_ID = 0x4256                         # 'RV'

# Mission Reference Time Epoch (UTC)
MISSION_EPOCH_ISO = "2027-03-14T00:00:00Z"
MISSION_EPOCH = datetime(2027, 3, 14, 0, 0, 0, tzinfo=timezone.utc)

# -----------------------------------------------------------------------------
# Pass API & Downlink Budget
# -----------------------------------------------------------------------------
DEFAULT_TEAM_CREDITS = 12
PASS_WINDOW_DURATION_S = 600   # 10 minutes = 600 frames
PASS_FRAME_COUNT = 600
PASS_BYTE_SIZE = PASS_FRAME_COUNT * FRAME_SIZE_BYTES  # 26,400 bytes
PASS_RATE_LIMIT_S = 20         # 1 pass per 20s
PASS_DEDUP_WINDOW_S = 300      # 5 minutes free re-fetch

# -----------------------------------------------------------------------------
# Challenge Points & Scoring Structure
# -----------------------------------------------------------------------------
CHALLENGE_POINTS = {
    # Phase 1
    "C1.1": 100,  # Clock drift rate / Epoch start
    "C1.2": 100,  # Data gap start & duration
    "C1.3": 100,  # Tick counter rollover timestamp
    
    # Phase 2
    "C2.1": 200,  # Fault 1 (EPS-07) onset UTC & code
    "C2.2": 200,  # Fault 2 (THM-03) onset UTC & code
    "C2.3": 250,  # Fault 3 (ADCS-02) cascade onset UTC & code
    "C2.4": 200,  # Fault 4 (COM-04) corrupted frame ID & code
    
    # Phase 3
    "C3.1": 200,  # Fault 3 cascade parameter sequence
    "C3.2": 150,  # OBC reset timestamp
    "C3.3": 250,  # Flipped bit index & recovered bat voltage
    "C3.4": 150,  # F1 orbit number & post-eclipse battery voltage
    
    # Bonus Track
    "B1.1": 150,  # Forged command ID
    "B1.2": 100,  # Replayed command ID
    
    # Live Contingency Finale
    "FINALE": 500 # Base finale points (+ up to 200 speed bonus)
}

# Scoring Rules
MAX_ATTEMPTS_PER_CHALLENGE = 5
COOLDOWN_DURATION_S = 600      # 10 minute cooldown after 5 failed attempts
WRONG_ATTEMPT_PENALTY_PCT = 0.05  # -5% points per wrong attempt
MAX_TIME_BONUS_PCT = 0.30      # Up to +30% time bonus
TIME_BONUS_DECAY_WINDOW_S = 7200 # 120 minutes decay window
FIRST_SOLVER_BONUS_PCT = 0.10  # +10% bonus for first solver across competition

# -----------------------------------------------------------------------------
# Directories
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DATA_DIR = os.path.join(BASE_DIR, "generated_data")
TEAMS_DATA_DIR = os.path.join(GENERATED_DATA_DIR, "teams")
SERVER_ARCHIVES_DIR = os.path.join(GENERATED_DATA_DIR, "server_archives")
ANSWERS_DIR = os.path.join(GENERATED_DATA_DIR, "answers")
DB_PATH = os.path.join(BASE_DIR, "challenge.db")
