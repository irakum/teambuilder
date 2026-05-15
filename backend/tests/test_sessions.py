import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestCreateSession:
    async def test_create_returns_201(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Хакатон 2026",
            "team_count": 3,
        })
        assert resp.status_code == 201

    async def test_response_has_token(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Тест", "team_count": 2,
        })
        data = resp.json()
        assert data["organizer_token"] is not None
        assert len(data["organizer_token"]) > 10

    async def test_response_has_correct_fields(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Мій захід",
            "team_count": 4,
            "min_team_size": 2,
            "max_team_size": 8,
        })
        data = resp.json()
        assert data["name"] == "Мій захід"
        assert data["team_count"] == 4
        assert data["status"] == "pending"
        assert data["participants"] == []
        assert data["teams"] == []

    async def test_invalid_team_count_below_2(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Тест", "team_count": 1,
        })
        assert resp.status_code == 422

    async def test_invalid_team_count_above_20(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Тест", "team_count": 21,
        })
        assert resp.status_code == 422

    async def test_min_size_greater_than_max_size(self, client: AsyncClient):
        resp = await client.post("/api/sessions", json={
            "name": "Тест", "team_count": 2,
            "min_team_size": 10, "max_team_size": 3,
        })
        assert resp.status_code == 422


class TestGetSession:
    async def test_get_existing_session(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        resp = await client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sid
        # Токен не має повертатись при GET
        assert data["organizer_token"] is None

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestDeleteSession:
    async def test_delete_with_valid_token(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.delete(
            f"/api/sessions/{sid}",
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 200
        # Сесія справді видалена
        get_resp = await client.get(f"/api/sessions/{sid}")
        assert get_resp.status_code == 404

    async def test_delete_without_token_returns_401(self, client: AsyncClient, session_data: dict):
        resp = await client.delete(f"/api/sessions/{session_data['id']}")
        assert resp.status_code == 401

    async def test_delete_with_wrong_token_returns_403(self, client: AsyncClient, session_data: dict):
        resp = await client.delete(
            f"/api/sessions/{session_data['id']}",
            headers={"X-Organizer-Token": "wrong-token"},
        )
        assert resp.status_code == 403
