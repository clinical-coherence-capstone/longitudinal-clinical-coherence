"""Tests for webapp/auth.py."""
import sys
import os
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp import database, auth


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up an isolated temporary database for each test."""
    test_db = tmp_path / "test_lcc_auth.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


def test_hash_password_not_plain():
    hashed = auth.hash_password("mysecretpassword")
    assert hashed != "mysecretpassword"
    assert isinstance(hashed, str)


def test_verify_password_correct():
    plain = "secure_pass_123"
    hashed = auth.hash_password(plain)
    assert auth.verify_password(plain, hashed) is True


def test_verify_password_wrong():
    plain = "secure_pass_123"
    hashed = auth.hash_password(plain)
    assert auth.verify_password("wrong_password", hashed) is False


def test_register_user_success():
    ok, msg = auth.register_user("alice", "password123")
    assert ok is True
    assert "successful" in msg.lower()


def test_register_short_password():
    ok, msg = auth.register_user("bob", "short")
    assert ok is False
    assert "at least" in msg.lower()


def test_register_duplicate_username():
    ok1, _ = auth.register_user("charlie", "password123")
    assert ok1 is True
    ok2, msg2 = auth.register_user("charlie", "password456")
    assert ok2 is False
    assert "already taken" in msg2.lower()


def test_login_success():
    auth.register_user("dan", "password123")
    ok, msg, uid = auth.login_user("dan", "password123")
    assert ok is True
    assert isinstance(uid, int)
    assert uid > 0


def test_login_wrong_password():
    auth.register_user("eve", "password123")
    ok, msg, uid = auth.login_user("eve", "wrong_password")
    assert ok is False
    assert uid is None
    assert "invalid credentials" in msg.lower()


def test_login_unknown_user():
    ok, msg, uid = auth.login_user("nonexistent_user", "password123")
    assert ok is False
    assert uid is None
    assert "invalid credentials" in msg.lower()
