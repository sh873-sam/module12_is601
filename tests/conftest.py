import socket
import subprocess
import time
import logging
from typing import Generator, Dict, List
from contextlib import contextmanager

import pytest
import requests
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, get_engine, get_sessionmaker
from app.models.user import User
from app.core.config import settings
from app.database_init import init_db, drop_db

# ======================================================================================
# Logging Configuration
# ======================================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ======================================================================================
# Database Configuration
# ======================================================================================

fake = Faker()
Faker.seed(12345)

test_engine = get_engine(database_url=settings.DATABASE_URL)
TestingSessionLocal = get_sessionmaker(engine=test_engine)

# ======================================================================================
# Helper Functions
# ======================================================================================

def create_fake_user() -> Dict[str, str]:
    """Generate fake user data."""
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "username": fake.unique.user_name(),
        "password": fake.password(length=12),
    }


@contextmanager
def managed_db_session():
    """Safe database session manager."""
    session = TestingSessionLocal()

    try:
        yield session

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise

    finally:
        session.close()

# ======================================================================================
# Server Health Check
# ======================================================================================

def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for FastAPI server to become available."""

    start_time = time.time()

    while (time.time() - start_time) < timeout:
        try:
            response = requests.get(url)

            if response.status_code == 200:
                return True

        except requests.exceptions.ConnectionError:
            time.sleep(1)

    return False


class ServerStartupError(Exception):
    """Raised when FastAPI server fails to start."""
    pass

# ======================================================================================
# Database Fixtures
# ======================================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_database(request):
    """Initialize test database."""

    logger.info("Setting up test database...")

    try:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        init_db()

        logger.info("Test database initialized.")

    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise

    yield

    if not request.config.getoption("--preserve-db"):
        logger.info("Dropping test database...")
        drop_db()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide isolated database session for tests."""

    session = TestingSessionLocal()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()

# ======================================================================================
# User Fixtures
# ======================================================================================

@pytest.fixture
def fake_user_data() -> Dict[str, str]:
    """Return fake user data."""
    return create_fake_user()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create test user."""

    user_data = create_fake_user()

    user = User(**user_data)

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    logger.info(f"Created test user: {user.id}")

    return user


@pytest.fixture
def seed_users(db_session: Session, request) -> List[User]:
    """Seed multiple users."""

    num_users = getattr(request, "param", 5)

    users = [User(**create_fake_user()) for _ in range(num_users)]

    db_session.add_all(users)
    db_session.commit()

    logger.info(f"Seeded {len(users)} users")

    return users

# ======================================================================================
# FastAPI Test Server
# ======================================================================================

def find_available_port() -> int:
    """Find open port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def fastapi_server():
    """Launch FastAPI test server."""

    base_port = 8000
    server_url = f"http://127.0.0.1:{base_port}/"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", base_port)) == 0:
            base_port = find_available_port()
            server_url = f"http://127.0.0.1:{base_port}/"

    logger.info(f"Starting FastAPI server on port {base_port}")

    process = subprocess.Popen(
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(base_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=".",
    )

    health_url = f"{server_url}health"

    if not wait_for_server(health_url, timeout=30):
        stderr = process.stderr.read()

        logger.error(f"Server failed to start: {stderr}")

        process.terminate()

        raise ServerStartupError(
            f"Failed to start server at {health_url}"
        )

    logger.info(f"Test server running at {server_url}")

    yield server_url

    logger.info("Stopping FastAPI server...")

    process.terminate()

    try:
        process.wait(timeout=5)

    except subprocess.TimeoutExpired:
        process.kill()

# ======================================================================================
# Pytest Options
# ======================================================================================

def pytest_addoption(parser):
    """Custom pytest options."""

    parser.addoption(
        "--preserve-db",
        action="store_true",
        help="Keep test database after tests"
    )

    parser.addoption(
        "--run-slow",
        action="store_true",
        help="Run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless requested."""

    if not config.getoption("--run-slow"):

        skip_slow = pytest.mark.skip(
            reason="Use --run-slow to run slow tests"
        )

        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)