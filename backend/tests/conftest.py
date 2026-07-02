import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings
from app.database.base import Base
from app.database.deps import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _no_real_external_credentials(monkeypatch):
    """The dev .env may have real OPENAI_API_KEY/ANTHROPIC_API_KEY (the live
    demo fallback, app/continuum/fallback.py) or a real SLACK_WEBHOOK_URL
    (app/integrations/slack/) set. Tests must never depend on - or
    accidentally trigger - real API spend or real Slack messages, so force
    all three unset by default. A test that specifically wants one of these
    present can still monkeypatch.setenv(...) itself; that call wins within
    that test since it runs after this fixture."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeRedis:
    """In-memory stand-in for the real Redis client, scoped to a single
    test. The project's own convention is that the test suite needs no
    Docker/Redis running at all - app/continuum/cache.py and app/core/jobs.py
    both talk to Redis directly, so without this, tests would either hit a
    real Redis (if one happens to be running locally, and even then risk a
    "RuntimeError: Event loop is closed" once the singleton client outlives
    the event loop of the test that first created it) or silently leak
    cached results between tests that reuse the same generic mock inputs."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value


# Every module that imports get_redis_client needs its own patch target
# here (Python binds `from x import y` at import time, so patching the
# source module doesn't reach already-imported references) - add a line
# for any new module that talks to Redis directly.
_REDIS_CONSUMER_MODULES = ["app.continuum.cache", "app.core.jobs"]


@pytest.fixture(autouse=True)
def _fake_continuum_cache(monkeypatch):
    fake = _FakeRedis()
    for module in _REDIS_CONSUMER_MODULES:
        monkeypatch.setattr(f"{module}.get_redis_client", lambda: fake)
    return fake


@pytest.fixture
async def db_session(monkeypatch):
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db

    # BackgroundTasks (e.g. app/api/frontend/development.py's compare job)
    # and the health monitor (app/services/health_monitor.py's poll loop)
    # run outside any request's DI scope, so they can't use the get_db
    # override above - they import AsyncSessionLocal directly instead. Patch
    # it at each *consuming* module's namespace so tests never touch the
    # real configured database. Add a line here for any new module that
    # adopts this same background-job pattern.
    monkeypatch.setattr("app.api.frontend.development.AsyncSessionLocal", session_factory)
    monkeypatch.setattr("app.services.health_monitor.AsyncSessionLocal", session_factory)

    async with session_factory() as session:
        yield session

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
