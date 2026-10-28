"""Security and authentication test suite."""
import pytest
from app.security.auth import hash_password, verify_password, create_user_session, validate_session, revoke_session
from app.security.csrf import generate_csrf_token, verify_csrf_token
from app.services.export_service import sanitize_csv_value

def test_password_hashing():
    pw = "SuperSecurePassword99!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False

def test_session_lifecycle(db_session, test_users):
    user = test_users["tourism_analyst"]
    session_obj, raw_token = create_user_session(db_session, user)

    # 1. Validate active session
    validated_user = validate_session(db_session, raw_token)
    assert validated_user is not None
    assert validated_user.id == user.id

    # 2. Revoke session on logout
    revoke_session(db_session, raw_token)
    assert validate_session(db_session, raw_token) is None

def test_csrf_token_verification():
    session_token = "secure_random_session_token_123"
    token = generate_csrf_token(session_token)
    assert token != ""
    assert verify_csrf_token(session_token, token) is True
    assert verify_csrf_token(session_token, "invalid_token_xyz") is False
    assert verify_csrf_token("different_session", token) is False

def test_csv_formula_injection_defense():
    # Danger formula prefixes: =, +, -, @, tab, carriage return
    assert sanitize_csv_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_value("+100") == "'+100"
    assert sanitize_csv_value("-250") == "'-250"
    assert sanitize_csv_value("@cmd|' /C calc'!A0") == "'@cmd|' /C calc'!A0"
    assert sanitize_csv_value("\tDangerousTab") == "'\tDangerousTab"
    assert sanitize_csv_value("\rDangerousCR") == "'\rDangerousCR"
    
    # Safe text left untouched
    assert sanitize_csv_value("Lake Toba") == "Lake Toba"
    assert sanitize_csv_value("1250000") == "1250000"
    assert sanitize_csv_value(None) == ""
