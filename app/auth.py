"""
Authentication and session management for teams and administrators.
"""
import hashlib
import os
import secrets
from datetime import datetime, timezone
from models import get_db_connection
from config import ADMIN_PASSWORD, MASTER_SECRET

def hash_password(password: str) -> str:
    """Hashes password with SHA256 + salt using PBKDF2."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${key.hex()}"

def verify_password(stored_hash: str, password_attempt: str) -> bool:
    """Verifies a password against the stored PBKDF2 hash."""
    try:
        salt, key_hex = stored_hash.split('$')
        key_attempt = hashlib.pbkdf2_hmac('sha256', password_attempt.encode('utf-8'), salt.encode('utf-8'), 100000)
        return secrets.compare_digest(key_hex, key_attempt.hex())
    except Exception:
        return False

def get_team_by_api_token(api_token: str):
    """Fetches team record by API token."""
    if not api_token:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE api_token = ?", (api_token,))
    team = cur.fetchone()
    conn.close()
    return team

def get_team_by_id(team_id: int):
    """Fetches team record by team ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
    team = cur.fetchone()
    conn.close()
    return team

def verify_admin_password(password: str) -> bool:
    """Checks admin password."""
    return secrets.compare_digest(password, ADMIN_PASSWORD)
