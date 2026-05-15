import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestDistribute:
    async def test_distribute_returns_200(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]

        resp = await client.post(
            f"/api/sessions/{sid}/distribute",
            json={"use_compatibility": True, "balance_threshold": 0.15},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 200

    async def test_distribute_creates_correct_team_count(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]

        resp = await client.post(
            f"/api/sessions/{sid}/distribute",
            json={},
            headers={"X-Organizer-Token": token},
        )
        data = resp.json()
        assert len(data["teams"]) == 2

    async def test_all_participants_assigned(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]

        resp = await client.post(
            f"/api/sessions/{sid}/distribute",
            json={},
            headers={"X-Organizer-Token": token},
        )
        data = resp.json()
        total = sum(len(t["participants"]) for t in data["teams"])
        assert total == 6

    async def test_status_becomes_distributed(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]

        await client.post(
            f"/api/sessions/{sid}/distribute",
            json={},
            headers={"X-Organizer-Token": token},
        )
        get_resp = await client.get(f"/api/sessions/{sid}")
        assert get_resp.json()["status"] == "distributed"

    async def test_teams_are_balanced(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]

        resp = await client.post(
            f"/api/sessions/{sid}/distribute",
            json={},
            headers={"X-Organizer-Token": token},
        )
        scores = [t["total_score"] for t in resp.json()["teams"]]
        assert abs(scores[0] - scores[1]) <= 5.0

    async def test_distribute_without_token_returns_401(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        resp = await client.post(f"/api/sessions/{sid}/distribute", json={})
        assert resp.status_code == 401

    async def test_distribute_empty_session_returns_422(
        self, client: AsyncClient, session_data: dict
    ):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/distribute",
            json={},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 422

    async def test_redistribute_resets_previous_results(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]
        headers = {"X-Organizer-Token": token}

        first = await client.post(f"/api/sessions/{sid}/distribute", json={}, headers=headers)
        first_teams = {t["id"] for t in first.json()["teams"]}

        second = await client.post(f"/api/sessions/{sid}/distribute", json={}, headers=headers)
        second_teams = {t["id"] for t in second.json()["teams"]}

        # Нові команди мають нові ID — старі видалені
        assert first_teams != second_teams
        assert len(second.json()["teams"]) == 2


class TestMoveParticipant:
    async def test_move_participant(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]
        headers = {"X-Organizer-Token": token}

        dist = await client.post(f"/api/sessions/{sid}/distribute", json={}, headers=headers)
        teams = dist.json()["teams"]

        # Беремо першого учасника першої команди і переміщуємо до другої
        participant_id = teams[0]["participants"][0]["id"]
        target_team_id = teams[1]["id"]

        resp = await client.patch(
            f"/api/sessions/{sid}/move-participant",
            json={"participant_id": participant_id, "target_team_id": target_team_id},
            headers=headers,
        )
        assert resp.status_code == 200

        # Перевіряємо що учасник справді у новій команді
        updated_teams = resp.json()["teams"]
        team1_ids = [p["id"] for p in next(t for t in updated_teams if t["id"] == teams[1]["id"])["participants"]]
        assert participant_id in team1_ids

    async def test_move_before_distribute_returns_422(
        self, client: AsyncClient, session_data: dict
    ):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.patch(
            f"/api/sessions/{sid}/move-participant",
            json={
                "participant_id": "00000000-0000-0000-0000-000000000001",
                "target_team_id": "00000000-0000-0000-0000-000000000002",
            },
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 422


class TestExport:
    async def test_export_csv_returns_bytes(
        self, client: AsyncClient, session_with_participants: dict
    ):
        sid = session_with_participants["id"]
        token = session_with_participants["organizer_token"]
        headers = {"X-Organizer-Token": token}

        await client.post(f"/api/sessions/{sid}/distribute", json={}, headers=headers)

        resp = await client.get(f"/api/sessions/{sid}/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert len(resp.content) > 0

    async def test_export_before_distribute_returns_422(
        self, client: AsyncClient, session_data: dict
    ):
        sid = session_data["id"]
        resp = await client.get(f"/api/sessions/{sid}/export/csv")
        assert resp.status_code == 422
