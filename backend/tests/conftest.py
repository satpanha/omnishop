"""
Pytest configuration and fixtures.
Configures an in-memory SQLite database for async integration tests.
"""

import os
import asyncio
from datetime import timedelta
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force development mode so mock auth tests work
os.environ["ENVIRONMENT"] = "development"
# Point the app's own engine at an (independent) in-memory SQLite so background
# notification tasks can never reach a real database; requests use the overridden
# test session below. Enable the payments feature and set a callback secret so the
# order/payment/webhook flow is exercisable offline (ABA runs in stub mode).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PAYMENTS_ENABLED"] = "true"
os.environ["ABA_PAYWAY_CALLBACK_SECRET"] = "test-callback-secret"

from app.main import app
from app.config import get_settings
from app.database import Base
from app.api.deps import get_db
from app.auth.jwt_handler import create_access_token

# Use async SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create and drop all database tables for each test run."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override yielding a test session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Apply dependency override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Direct session fixture for writing test setup data."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing endpoints."""
    # Using the new ASGITransport in httpx
    async with AsyncClient(
        transport=ASGITransport(app=app), # type: ignore
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_admin_token() -> str:
    """Generate a valid JWT token for an admin."""
    settings = get_settings()
    payload = {
        "sub": str(settings.ADMIN_TELEGRAM_ID),
        "role": "admin",
    }
    return create_access_token(payload, expires_delta=timedelta(minutes=10))


@pytest.fixture
def mock_buyer_token() -> str:
    """Generate a valid JWT for a standard buyer user."""
    payload = {
        "sub": "1234567890",
        "role": "buyer",
    }
    return create_access_token(payload, expires_delta=timedelta(minutes=10))
