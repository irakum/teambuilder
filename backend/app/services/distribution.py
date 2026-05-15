"""
Модуль алгоритму розподілу учасників у команди.

Не залежить від FastAPI, SQLAlchemy чи будь-яких зовнішніх бібліотек —
лише стандартна бібліотека Python. Це дозволяє тестувати логіку ізольовано.

Вхідні дані передаються як прості dataclass-об'єкти, результат повертається
у вигляді словника {team_index: [participant_id, ...]}.
"""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class SkillEntry:
    """Одна навичка учасника з її рівнем і ваговим коефіцієнтом."""
    name: str
    level: int       # 1–5
    weight: float    # ваговий коефіцієнт з таблиці skills


@dataclass
class ParticipantInput:
    """Учасник у вигляді, зручному для алгоритму."""
    id: UUID
    name: str
    skills: list[SkillEntry] = field(default_factory=list)
    compatibility_tags: list[str] = field(default_factory=list)


@dataclass
class TeamResult:
    """Результат розподілу для однієї команди."""
    index: int
    participant_ids: list[UUID] = field(default_factory=list)
    total_score: float = 0.0


# ── Крок 1: підрахунок рейтингу ──────────────────────────────────────────────

def calc_score(participant: ParticipantInput) -> float:
    """
    Обчислює зважений сумарний рейтинг навичок учасника.

    score = Σ (level_i × weight_i)

    Якщо навичок немає — рейтинг 0, учасник все одно бере участь у розподілі.
    """
    return sum(s.level * s.weight for s in participant.skills)


# ── Крок 2: жадібний розподіл ────────────────────────────────────────────────

def greedy_distribute(
    participants: list[ParticipantInput],
    team_count: int,
) -> list[TeamResult]:
    """
    Жадібний алгоритм рівномірного розподілу.

    Учасників сортуємо за спаданням рейтингу, потім по черзі
    призначаємо кожного до команди з найменшим поточним рейтингом.
    Складність: O(n log n) для сортування + O(n log k) для вибору мінімуму,
    де n — кількість учасників, k — кількість команд.
    """
    if team_count <= 0:
        raise ValueError("Кількість команд має бути більше 0")
    if not participants:
        return [TeamResult(index=i) for i in range(team_count)]

    scored = sorted(
        [(calc_score(p), p) for p in participants],
        key=lambda x: x[0],
        reverse=True,
    )

    teams: list[TeamResult] = [TeamResult(index=i) for i in range(team_count)]

    for score, participant in scored:
        # Команда з найменшим поточним сумарним рейтингом
        weakest = min(teams, key=lambda t: t.total_score)
        weakest.participant_ids.append(participant.id)
        weakest.total_score += score

    return teams


# ── Крок 3: коригування сумісності ───────────────────────────────────────────

def apply_compatibility(
    teams: list[TeamResult],
    participants: list[ParticipantInput],
    balance_threshold: float = 0.15,
) -> list[TeamResult]:
    """
    Коригує розподіл з урахуванням тегів сумісності.

    Якщо в одній команді є два учасники з однаковим тегом (наприклад,
    обидва мають тег "leader"), алгоритм намагається обміняти одного
    з них на учасника з іншої команди без цього тегу.

    Обмін виконується лише якщо він не погіршує загальний баланс
    більше ніж на balance_threshold (частка від середнього рейтингу команди).

    Параметр balance_threshold=0.15 означає допустиме відхилення 15%.
    """
    if not teams:
        return teams

    # Швидкий доступ до учасника за ID
    by_id: dict[UUID, ParticipantInput] = {p.id: p for p in participants}

    avg_score = sum(t.total_score for t in teams) / len(teams)
    max_delta = avg_score * balance_threshold

    changed = True
    max_passes = 10  # обмежуємо кількість проходів щоб уникнути нескінченного циклу

    while changed and max_passes > 0:
        changed = False
        max_passes -= 1

        for team in teams:
            # Знаходимо теги, що зустрічаються в команді більше одного разу
            tag_counts: dict[str, list[UUID]] = {}
            for pid in team.participant_ids:
                for tag in by_id[pid].compatibility_tags:
                    tag_counts.setdefault(tag, []).append(pid)

            conflicting_tags = {
                tag: pids for tag, pids in tag_counts.items() if len(pids) > 1
            }
            if not conflicting_tags:
                continue

            # Беремо першого учасника з конфліктуючим тегом для переміщення
            conflict_tag = next(iter(conflicting_tags))
            candidate_id = conflicting_tags[conflict_tag][1]  # залишаємо першого, переміщуємо другого
            candidate = by_id[candidate_id]
            candidate_score = calc_score(candidate)

            # Шукаємо команду для обміну
            for other_team in teams:
                if other_team.index == team.index:
                    continue

                for other_pid in other_team.participant_ids:
                    other = by_id[other_pid]

                    # Учасник не має конфліктуючого тегу
                    if conflict_tag in other.compatibility_tags:
                        continue

                    # Учасник, якого приймає поточна команда, не створить нових конфліктів
                    other_tags_in_team = {
                        tag
                        for pid in team.participant_ids
                        if pid != candidate_id
                        for tag in by_id[pid].compatibility_tags
                    }
                    if any(tag in other_tags_in_team for tag in other.compatibility_tags):
                        continue

                    other_score = calc_score(other)
                    score_diff = abs(candidate_score - other_score)

                    # Обмін не погіршує баланс суттєво
                    if score_diff > max_delta:
                        continue

                    # Виконуємо обмін
                    team.participant_ids.remove(candidate_id)
                    team.participant_ids.append(other_pid)
                    team.total_score = team.total_score - candidate_score + other_score

                    other_team.participant_ids.remove(other_pid)
                    other_team.participant_ids.append(candidate_id)
                    other_team.total_score = other_team.total_score - other_score + candidate_score

                    changed = True
                    break

                if changed:
                    break

    return teams


# ── Публічний інтерфейс ───────────────────────────────────────────────────────

def distribute(
    participants: list[ParticipantInput],
    team_count: int,
    use_compatibility: bool = True,
    balance_threshold: float = 0.15,
) -> list[TeamResult]:
    """
    Головна функція розподілу. Координує всі три етапи:
    1. Обчислення рейтингів (вбудовано в greedy_distribute через calc_score).
    2. Жадібний розподіл.
    3. Коригування сумісності (опціонально).

    Повертає список TeamResult відсортований за індексом команди.
    """
    teams = greedy_distribute(participants, team_count)

    if use_compatibility and any(p.compatibility_tags for p in participants):
        teams = apply_compatibility(teams, participants, balance_threshold)

    return sorted(teams, key=lambda t: t.index)
