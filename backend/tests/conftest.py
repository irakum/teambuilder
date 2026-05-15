import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def session_data(client: AsyncClient) -> dict:
    resp = await client.post("/api/sessions", json={
        "name": "Тест хакатон",
        "team_count": 2,
        "min_team_size": 1,
        "max_team_size": 10,
    })
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def session_with_participants(client: AsyncClient, session_data: dict) -> dict:
    sid = session_data["id"]
    token = session_data["organizer_token"]
    headers = {"X-Organizer-Token": token}

    participants = [
        {"name": "Аня",    "skills": [{"name": "Python", "level": 5}], "compatibility_tags": ["leader"]},
        {"name": "Боря",   "skills": [{"name": "Python", "level": 3}], "compatibility_tags": []},
        {"name": "Вася",   "skills": [{"name": "Design", "level": 4}], "compatibility_tags": ["leader"]},
        {"name": "Галя",   "skills": [{"name": "Design", "level": 2}], "compatibility_tags": []},
        {"name": "Дмитро", "skills": [{"name": "React",  "level": 5}], "compatibility_tags": []},
        {"name": "Олена",  "skills": [{"name": "React",  "level": 3}], "compatibility_tags": []},
    ]
    for p in participants:
        r = await client.post(
            f"/api/sessions/{sid}/participants", json=p, headers=headers
        )
        assert r.status_code == 201

    return session_data