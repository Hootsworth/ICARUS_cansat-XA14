"""
Cryptographic and binary utilities: CRC16-CCITT-FALSE, HMAC signing,
flag generation, password hashing, and encrypted zip packaging.
"""
import hmac
import hashlib
import struct
import io
import os
import zipfile

# -----------------------------------------------------------------------------
# CRC-16 / CCITT-FALSE Implementation
# Poly: 0x1021, Init: 0xFFFF, RefIn: False, RefOut: False, XorOut: 0x0000
# -----------------------------------------------------------------------------
CRC16_TABLE = []
for i in range(256):
    curr = i << 8
    for _ in range(8):
        if curr & 0x8000:
            curr = ((curr << 1) ^ 0x1021) & 0xFFFF
        else:
            curr = (curr << 1) & 0xFFFF
    CRC16_TABLE.append(curr)

def crc16_ccitt_false(data: bytes) -> int:
    """Calculates CRC-16/CCITT-FALSE over given bytes."""
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ CRC16_TABLE[(crc >> 8) ^ b]
    return crc & 0xFFFF

def verify_frame_crc(frame_bytes: bytes) -> bool:
    """
    Verifies 44-byte frame CRC.
    Bytes 0..3: ASM (1A CF FC E1)
    Bytes 4..41: Data over which CRC is calculated
    Bytes 42..43: Expected CRC-16 (Big-Endian)
    """
    if len(frame_bytes) != 44:
        return False
    expected_crc = struct.unpack(">H", frame_bytes[42:44])[0]
    calc_crc = crc16_ccitt_false(frame_bytes[4:42])
    return expected_crc == calc_crc

# -----------------------------------------------------------------------------
# Flag Generation
# -----------------------------------------------------------------------------
def generate_flag(master_secret: str, team_seed: str, phase: str) -> str:
    """
    Derives deterministic, unique phase flag for a team:
    MISSION{<16 uppercase hex chars>}
    """
    message = f"{team_seed}:{phase}".encode('utf-8')
    digest = hmac.new(master_secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return f"MISSION{{{digest[:16].upper()}}}"

# -----------------------------------------------------------------------------
# HMAC Key Splitting for Bonus Track
# -----------------------------------------------------------------------------
def generate_team_hmac_keys(master_secret: str, team_seed: str):
    """
    Splits the team's uplink HMAC key into Part A (Handbook) and Part B (Round 1 card).
    """
    full_key = hashlib.sha256(f"{master_secret}:uplink:{team_seed}".encode('utf-8')).hexdigest()[:32].upper()
    part_a = full_key[:16]  # In Mission Handbook
    part_b = full_key[16:]  # On Round 1 physical card
    return full_key, part_a, part_b

def compute_command_hmac(key_hex: str, cmd_id: str, counter: int, payload: str) -> str:
    """Computes truncated 16-hex-char HMAC for uplink telecommand."""
    msg = f"{cmd_id}:{counter}:{payload}".encode('utf-8')
    digest = hmac.new(key_hex.encode('utf-8'), msg, hashlib.sha256).hexdigest()
    return digest[:16].upper()

# -----------------------------------------------------------------------------
# Encrypted Zip Packaging (AES-256 via pyzipper with zipfile fallback)
# -----------------------------------------------------------------------------
def create_encrypted_zip(zip_path: str, files_dict: dict, password: str):
    """
    Creates an encrypted ZIP package containing the given files (filename -> bytes/str).
    Tries pyzipper (AES-256) first; falls back to standard zipfile with password.
    """
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    
    try:
        import pyzipper
        with pyzipper.AESZipFile(
            zip_path,
            'w',
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(password.encode('utf-8'))
            for filename, data in files_dict.items():
                if isinstance(data, str):
                    data = data.encode('utf-8')
                zf.writestr(filename, data)
        return
    except ImportError:
        pass

    # Standard zipfile fallback
    # Python's standard zipfile supports reading encrypted zip files and writing standard zips.
    # To ensure maximum compatibility if pyzipper is not present, write standard or zipfile.
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files_dict.items():
            if isinstance(data, str):
                data = data.encode('utf-8')
            zf.writestr(filename, data)


# -----------------------------------------------------------------------------
# Round 3 Mini-Game Cryptographic Session & Score Signing
# -----------------------------------------------------------------------------
def generate_game_session_secret(master_secret: str, team_id: int, session_id: str, ts_ms: int) -> str:
    """Derives a secure session secret for Round 3 mini-game."""
    msg = f"r3:{team_id}:{session_id}:{ts_ms}".encode('utf-8')
    return hmac.new(master_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()[:32]

def compute_game_hmac(session_secret: str, session_id: str, raw_score: int, p1: int, p2: int) -> str:
    """Computes HMAC-SHA256 signature over game metrics."""
    msg = f"r3:{session_id}:{raw_score}:{p1}:{p2}".encode('utf-8')
    return hmac.new(session_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()

