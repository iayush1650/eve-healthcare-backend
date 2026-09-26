"""Pytest fixtures for API testing using an in-memory SQLite database."""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Override settings BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.booking import Booking, BookingStatus
from app.models.centre import DiagnosticCentre
from app.models.payment import Payment, PaymentStatus
from app.models.test import CentreTest, DiagnosticTest
from app.models.user import User

# ── In-Memory SQLite Engine for Tests ────────────────────────────────────────

SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def db_session():
    """Create tables and yield a fresh DB session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with dependency overrides."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> User:
    """Create and return a test user."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Return Authorization headers with a valid JWT for the test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_centre(db_session) -> DiagnosticCentre:
    """Create and return a test diagnostic centre."""
    centre = DiagnosticCentre(
        name="Test Diagnostics",
        location="Test City",
        address="123 Test Street",
        phone="+91-1234567890",
    )
    db_session.add(centre)
    db_session.commit()
    db_session.refresh(centre)
    return centre


@pytest.fixture
def test_diagnostic_test(db_session) -> DiagnosticTest:
    """Create and return a test diagnostic test."""
    test = DiagnosticTest(
        name="Complete Blood Count",
        description="Full blood count test",
        category="Hematology",
    )
    db_session.add(test)
    db_session.commit()
    db_session.refresh(test)
    return test


@pytest.fixture
def test_centre_test(db_session, test_centre, test_diagnostic_test) -> CentreTest:
    """Create and return a centre-test link with pricing."""
    ct = CentreTest(
        centre_id=test_centre.id,
        test_id=test_diagnostic_test.id,
        price=Decimal("500.00"),
        is_available=True,
    )
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return ct


@pytest.fixture
def test_booking(db_session, test_user, test_centre_test) -> Booking:
    """Create and return a test booking."""
    booking = Booking(
        user_id=test_user.id,
        centre_test_id=test_centre_test.id,
        appointment_datetime=datetime.now(timezone.utc) + timedelta(days=7),
        amount=test_centre_test.price,
        status=BookingStatus.PENDING,
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


@pytest.fixture
def test_payment(db_session, test_booking) -> Payment:
    """Create and return a test payment."""
    payment = Payment(
        booking_id=test_booking.id,
        transaction_id="TXN-TEST123456",
        amount=test_booking.amount,
        status=PaymentStatus.PENDING,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment
