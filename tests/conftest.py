"""Test fixtures, temporary SQLite database, and authenticated test clients."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.database import Base, get_db
from app.config import settings
from app.models.entities import User
from app.security.auth import hash_password, create_user_session
from app.security.csrf import generate_csrf_token
from app.services.demo_data_service import seed_destinations_and_segments, generate_lake_toba_demo_dataset
from app.main import app

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=eng)
    return eng

@pytest.fixture
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    seed_destinations_and_segments(session)
    yield session
    session.close()

@pytest.fixture
def test_users(db_session):
    """Seed test users for each role."""
    roles = ["business_owner", "tourism_analyst", "marketing_manager", "read_only_executive"]
    users = {}
    for r in roles:
        u = db_session.query(User).filter(User.username == f"test_{r}").first()
        if not u:
            u = User(
                username=f"test_{r}",
                email=f"{r}@test.local",
                password_hash=hash_password("Password123!"),
                role=r,
                is_active=True
            )
            db_session.add(u)
            db_session.commit()
            db_session.refresh(u)
        users[r] = u
    return users

@pytest.fixture
def seeded_dataset(db_session):
    """Seed synthetic benchmark dataset."""
    return generate_lake_toba_demo_dataset(db_session, seed=42)

@pytest.fixture
def client(db_session):
    """Test client overriding the database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def auth_client_for_user(client: TestClient, db_session, user: User) -> str:
    """Helper to authenticate test client and return valid CSRF token."""
    _, raw_token = create_user_session(db_session, user)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    return generate_csrf_token(raw_token)
