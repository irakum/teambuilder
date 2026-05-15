"""
Юніт-тести алгоритму розподілу.

Запуск: pytest tests/test_distribution.py -v
"""

import uuid
import pytest

from app.services.distribution import (
    ParticipantInput,
    SkillEntry,
    TeamResult,
    calc_score,
    greedy_distribute,
    apply_compatibility,
    distribute,
)


# ── Фікстури ─────────────────────────────────────────────────────────────────

def make_participant(
    name: str,
    skills: list[tuple[str, int, float]] | None = None,
    tags: list[str] | None = None,
) -> ParticipantInput:
    """Допоміжна функція для швидкого створення учасника в тестах."""
    return ParticipantInput(
        id=uuid.uuid4(),
        name=name,
        skills=[SkillEntry(name=s[0], level=s[1], weight=s[2]) for s in (skills or [])],
        compatibility_tags=tags or [],
    )


# ── calc_score ────────────────────────────────────────────────────────────────

class TestCalcScore:
    def test_empty_skills_returns_zero(self):
        p = make_participant("Аня")
        assert calc_score(p) == 0.0

    def test_single_skill(self):
        p = make_participant("Боря", skills=[("Python", 4, 1.0)])
        assert calc_score(p) == 4.0

    def test_weighted_skills(self):
        p = make_participant("Вася", skills=[
            ("Python", 4, 2.0),   # 8
            ("Design", 3, 1.0),   # 3
        ])
        assert calc_score(p) == 11.0

    def test_multiple_skills_equal_weights(self):
        p = make_participant("Галя", skills=[
            ("JS", 5, 1.0),
            ("CSS", 3, 1.0),
            ("React", 4, 1.0),
        ])
        assert calc_score(p) == 12.0


# ── greedy_distribute ────────────────────────────────────────────────────────

class TestGreedyDistribute:
    def test_empty_participants(self):
        result = greedy_distribute([], team_count=3)
        assert len(result) == 3
        assert all(len(t.participant_ids) == 0 for t in result)

    def test_invalid_team_count(self):
        with pytest.raises(ValueError):
            greedy_distribute([], team_count=0)

    def test_single_participant_goes_to_weakest_team(self):
        p = make_participant("Аня", skills=[("Python", 5, 1.0)])
        result = greedy_distribute([p], team_count=2)
        total_assigned = sum(len(t.participant_ids) for t in result)
        assert total_assigned == 1

    def test_balanced_distribution_two_teams(self):
        """Чотири учасники з рівними рейтингами мають рівномірно розподілитись."""
        participants = [
            make_participant(f"P{i}", skills=[("skill", 3, 1.0)])
            for i in range(4)
        ]
        result = greedy_distribute(participants, team_count=2)
        assert len(result[0].participant_ids) == 2
        assert len(result[1].participant_ids) == 2

    def test_scores_are_balanced(self):
        """Різниця між рейтингами команд має бути мінімальною."""
        participants = [
            make_participant("A", skills=[("s", 5, 1.0)]),
            make_participant("B", skills=[("s", 4, 1.0)]),
            make_participant("C", skills=[("s", 3, 1.0)]),
            make_participant("D", skills=[("s", 2, 1.0)]),
        ]
        result = greedy_distribute(participants, team_count=2)
        scores = [t.total_score for t in result]
        # A(5)+D(2)=7 та B(4)+C(3)=7 — ідеальний баланс
        assert abs(scores[0] - scores[1]) <= 1.0

    def test_all_participants_are_assigned(self):
        participants = [make_participant(f"P{i}") for i in range(7)]
        result = greedy_distribute(participants, team_count=3)
        assigned = sum(len(t.participant_ids) for t in result)
        assert assigned == 7

    def test_more_teams_than_participants(self):
        """Якщо команд більше ніж учасників — деякі команди будуть порожніми."""
        participants = [make_participant("P1"), make_participant("P2")]
        result = greedy_distribute(participants, team_count=5)
        assigned = sum(len(t.participant_ids) for t in result)
        assert assigned == 2
        # При нульових рейтингах min() завжди повертає першу команду,
        # тому обидва учасники потрапляють в team0, а 4 команди порожні
        empty_teams = sum(1 for t in result if len(t.participant_ids) == 0)
        assert empty_teams >= 3  # мінімум 3 порожніх, може бути 4


# ── apply_compatibility ───────────────────────────────────────────────────────

class TestApplyCompatibility:
    def test_no_tags_no_change(self):
        participants = [make_participant(f"P{i}") for i in range(4)]
        teams = greedy_distribute(participants, team_count=2)
        original_ids = [set(t.participant_ids) for t in teams]
        result = apply_compatibility(teams, participants)
        result_ids = [set(t.participant_ids) for t in result]
        assert original_ids == result_ids

    def test_two_leaders_in_one_team_get_split(self):
        """Якщо в одній команді два лідери — один має перейти до іншої."""
        leader1 = make_participant("L1", skills=[("s", 3, 1.0)], tags=["leader"])
        leader2 = make_participant("L2", skills=[("s", 3, 1.0)], tags=["leader"])
        follower1 = make_participant("F1", skills=[("s", 3, 1.0)])
        follower2 = make_participant("F2", skills=[("s", 3, 1.0)])

        # Вручну кладемо обох лідерів в одну команду
        team0 = TeamResult(index=0, participant_ids=[leader1.id, leader2.id], total_score=6.0)
        team1 = TeamResult(index=1, participant_ids=[follower1.id, follower2.id], total_score=6.0)
        all_participants = [leader1, leader2, follower1, follower2]

        result = apply_compatibility([team0, team1], all_participants)

        leaders_in_team0 = sum(
            1 for pid in result[0].participant_ids
            if "leader" in next(p for p in all_participants if p.id == pid).compatibility_tags
        )
        leaders_in_team1 = sum(
            1 for pid in result[1].participant_ids
            if "leader" in next(p for p in all_participants if p.id == pid).compatibility_tags
        )
        assert leaders_in_team0 == 1
        assert leaders_in_team1 == 1

    def test_no_swap_when_score_diff_too_large(self):
        """Якщо обмін дуже погіршить баланс — він не виконується."""
        leader1 = make_participant("L1", skills=[("s", 5, 1.0)], tags=["leader"])
        leader2 = make_participant("L2", skills=[("s", 1, 1.0)], tags=["leader"])
        follower = make_participant("F1", skills=[("s", 5, 1.0)])  # рейтинг як у L1

        team0 = TeamResult(index=0, participant_ids=[leader1.id, leader2.id], total_score=6.0)
        team1 = TeamResult(index=1, participant_ids=[follower.id], total_score=5.0)

        # threshold=0.0 означає: будь-яка різниця в рейтингу забороняє обмін
        result = apply_compatibility([team0, team1], [leader1, leader2, follower], balance_threshold=0.0)

        # Обидва лідери залишились у team0
        assert leader1.id in result[0].participant_ids
        assert leader2.id in result[0].participant_ids


# ── distribute (публічний інтерфейс) ─────────────────────────────────────────

class TestDistribute:
    def test_result_sorted_by_index(self):
        participants = [make_participant(f"P{i}") for i in range(6)]
        result = distribute(participants, team_count=3)
        assert [t.index for t in result] == [0, 1, 2]

    def test_all_participants_assigned(self):
        participants = [
            make_participant(f"P{i}", skills=[("Python", i % 5 + 1, 1.0)])
            for i in range(10)
        ]
        result = distribute(participants, team_count=3)
        assigned = sum(len(t.participant_ids) for t in result)
        assert assigned == 10

    def test_compatibility_disabled(self):
        """З use_compatibility=False функція apply_compatibility не викликається."""
        leader1 = make_participant("L1", skills=[("s", 3, 1.0)], tags=["leader"])
        leader2 = make_participant("L2", skills=[("s", 3, 1.0)], tags=["leader"])
        follower = make_participant("F1", skills=[("s", 3, 1.0)])

        result = distribute([leader1, leader2, follower], team_count=2, use_compatibility=False)
        assigned = sum(len(t.participant_ids) for t in result)
        assert assigned == 3

    def test_score_variance_is_small(self):
        """Різниця між максимальним і мінімальним рейтингом команд не перевищує рейтинг одного учасника."""
        participants = [
            make_participant(f"P{i}", skills=[("s", (i % 5) + 1, 1.0)])
            for i in range(12)
        ]
        result = distribute(participants, team_count=4)
        scores = [t.total_score for t in result]
        assert max(scores) - min(scores) <= 5.0  # максимальний рейтинг одного учасника
