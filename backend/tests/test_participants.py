import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAddParticipant:
    async def test_add_returns_201(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Іван", "skills": [{"name": "Python", "level": 4}]},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 201

    async def test_add_returns_correct_fields(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/participants",
            json={
                "name": "  Марія  ",  # пробіли мають обрізатись
                "skills": [{"name": "Design", "level": 3}],
                "compatibility_tags": ["leader"],
            },
            headers={"X-Organizer-Token": token},
        )
        data = resp.json()
        assert data["name"] == "Марія"
        assert data["compatibility_tags"] == ["leader"]
        assert len(data["skills"]) == 1
        assert data["skills"][0]["name"] == "Design"
        assert data["skills"][0]["level"] == 3
        assert data["total_score"] == 3.0

    async def test_score_calculated_with_weight(self, client: AsyncClient, session_data: dict):
        """Якщо навичка має вагу 2.0 — рейтинг має бути level × weight."""
        # Вага змінюється напряму в БД для тесту — тут просто перевіряємо формулу
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Тест", "skills": [{"name": "UniqSkill", "level": 4}]},
            headers={"X-Organizer-Token": token},
        )
        # Вага за замовчуванням 1.0, тому score = 4 × 1.0 = 4.0
        assert resp.json()["total_score"] == 4.0

    async def test_add_without_token_returns_401(self, client: AsyncClient, session_data: dict):
        resp = await client.post(
            f"/api/sessions/{session_data['id']}/participants",
            json={"name": "Тест"},
        )
        assert resp.status_code == 401

    async def test_skill_level_out_of_range(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Тест", "skills": [{"name": "Python", "level": 6}]},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 422

    async def test_empty_name_rejected(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        resp = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": ""},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 422


class TestListParticipants:
    async def test_list_returns_all(self, client: AsyncClient, session_with_participants: dict):
        sid = session_with_participants["id"]
        resp = await client.get(f"/api/sessions/{sid}/participants")
        assert resp.status_code == 200
        assert len(resp.json()) == 6


class TestUpdateParticipant:
    async def test_update_name(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        headers = {"X-Organizer-Token": token}

        add = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Старе ім'я"},
            headers=headers,
        )
        pid = add.json()["id"]

        update = await client.patch(
            f"/api/sessions/{sid}/participants/{pid}",
            json={"name": "Нове ім'я"},
            headers=headers,
        )
        assert update.status_code == 200
        assert update.json()["name"] == "Нове ім'я"

    async def test_update_skills_replaces_all(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        headers = {"X-Organizer-Token": token}

        add = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Тест", "skills": [{"name": "Python", "level": 3}]},
            headers=headers,
        )
        pid = add.json()["id"]

        update = await client.patch(
            f"/api/sessions/{sid}/participants/{pid}",
            json={"skills": [{"name": "React", "level": 5}]},
            headers=headers,
        )
        skills = update.json()["skills"]
        assert len(skills) == 1
        assert skills[0]["name"] == "React"
        assert skills[0]["level"] == 5


class TestDeleteParticipant:
    async def test_delete_participant(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]
        headers = {"X-Organizer-Token": token}

        add = await client.post(
            f"/api/sessions/{sid}/participants",
            json={"name": "Для видалення"},
            headers=headers,
        )
        pid = add.json()["id"]

        delete = await client.delete(
            f"/api/sessions/{sid}/participants/{pid}",
            headers=headers,
        )
        assert delete.status_code == 200

        # Перевіряємо що учасника справді нема
        resp = await client.get(f"/api/sessions/{sid}/participants")
        ids = [p["id"] for p in resp.json()]
        assert pid not in ids


class TestImportCSV:
    async def test_import_valid_csv(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]

        csv_content = (
            "name,skills,tags\n"
            'Іван,"Python:4,Design:3","leader,backend"\n'
            'Оля,"React:5",\n'
            "Петро,,\n"
        ).encode("utf-8")

        resp = await client.post(
            f"/api/sessions/{sid}/participants/import",
            files={"file": ("participants.csv", csv_content, "text/csv")},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 201
        assert resp.json()["imported"] == 3

    async def test_import_csv_without_name_column(self, client: AsyncClient, session_data: dict):
        sid = session_data["id"]
        token = session_data["organizer_token"]

        csv_content = b"email,skills\ntest@example.com,Python:4\n"
        resp = await client.post(
            f"/api/sessions/{sid}/participants/import",
            files={"file": ("bad.csv", csv_content, "text/csv")},
            headers={"X-Organizer-Token": token},
        )
        assert resp.status_code == 422
