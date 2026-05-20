"""
WebSocket чат.

Канали:
  general                — загальний чат хакатону
  team:{team_id}         — командний чат
  support:{participant_id} — підтримка: учасник ↔ всі організатори

Підключення: ws://.../api/ws/{session_id}?token={jwt}&channel={channel}
"""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import DefaultDict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.jwt import decode_token
from app.db.session import get_db
from app.models.message import Message
from app.models.participant import Participant
from app.models.session import Session
from app.models.session_organizer import SessionOrganizer
from app.models.user import User

router = APIRouter(tags=["chat"])


# ── ConnectionManager ─────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        # session_id → channel_key → list of (ws, user_id)
        self._connections: DefaultDict[str, DefaultDict[str, list]] = defaultdict(lambda: defaultdict(list))

    def _key(self, session_id: str, channel: str) -> tuple[str, str]:
        return session_id, channel

    async def connect(self, ws: WebSocket, session_id: str, channel: str, user_id: str) -> None:
        await ws.accept()
        self._connections[session_id][channel].append((ws, user_id))

    def disconnect(self, ws: WebSocket, session_id: str, channel: str) -> None:
        conns = self._connections[session_id][channel]
        self._connections[session_id][channel] = [(w, u) for w, u in conns if w is not ws]

    async def broadcast(self, session_id: str, channel: str, data: dict) -> None:
        for ws, _ in list(self._connections[session_id][channel]):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def send_to_user(self, session_id: str, channel: str, user_id: str, data: dict) -> None:
        for ws, uid in list(self._connections[session_id][channel]):
            if uid == user_id:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass


manager = ConnectionManager()


# ── Допоміжні функції ─────────────────────────────────────────────────────────

async def _get_user_from_token(token: str, db: AsyncSession) -> User | None:
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
    except Exception:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def _is_organizer(session_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        return False
    if str(session.owner_id) == str(user_id):
        return True
    co_result = await db.execute(
        select(SessionOrganizer).where(
            SessionOrganizer.session_id == session_id,
            SessionOrganizer.user_id == user_id,
        )
    )
    return co_result.scalar_one_or_none() is not None


async def _get_participant(session_id: UUID, user_id: UUID, db: AsyncSession) -> Participant | None:
    result = await db.execute(
        select(Participant).where(
            Participant.session_id == session_id,
            Participant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _load_history(session_id: UUID, channel: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id, Message.channel == channel)
        .options(selectinload(Message.sender))
        .order_by(Message.created_at)
        .limit(100)
    )
    messages = result.scalars().all()
    return [_format(m) for m in messages]


async def _load_team_history(session_id: UUID, team_id: UUID, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.channel == "team",
            Message.team_id == team_id,
        )
        .options(selectinload(Message.sender))
        .order_by(Message.created_at)
        .limit(100)
    )
    return [_format(m) for m in result.scalars().all()]


async def _load_support_history(session_id: UUID, participant_id: UUID, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.channel == "support",
            Message.participant_id == participant_id,
        )
        .options(selectinload(Message.sender))
        .order_by(Message.created_at)
        .limit(100)
    )
    return [_format(m) for m in result.scalars().all()]


def _format(m: Message) -> dict:
    return {
        "id": str(m.id),
        "channel": m.channel,
        "sender_id": str(m.sender_id),
        "sender_name": m.sender.name if m.sender else "?",
        "sender_avatar": m.sender.avatar_url if m.sender else None,
        "team_id": str(m.team_id) if m.team_id else None,
        "participant_id": str(m.participant_id) if m.participant_id else None,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


# ── HTTP ендпоінт: список чатів для поточного юзера ──────────────────────────

from fastapi import Depends as FDepends
from app.api.dependencies import get_current_user


class ChatInfo:
    pass


from pydantic import BaseModel


class ChatListItem(BaseModel):
    channel: str          # "general" | "team:{id}" | "support:{participant_id}"
    title: str
    subtitle: str | None = None
    last_message_at: str | None = None


async def _get_last_message_at(session_id: UUID, channel: str, team_id: UUID | None, participant_id: UUID | None, db: AsyncSession) -> str | None:
    q = select(Message).where(
        Message.session_id == session_id,
        Message.channel == channel,
    )
    if team_id:
        q = q.where(Message.team_id == team_id)
    if participant_id:
        q = q.where(Message.participant_id == participant_id)
    q = q.order_by(Message.created_at.desc()).limit(1)
    result = await db.execute(q)
    msg = result.scalar_one_or_none()
    return msg.created_at.isoformat() if msg else None


@router.get("/sessions/{session_id}/chats", response_model=list[ChatListItem])
async def list_chats(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Повертає список доступних чатів для поточного юзера."""
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")

    is_org = await _is_organizer(session_id, current_user.id, db)
    participant = await _get_participant(session_id, current_user.id, db)

    chats: list[ChatListItem] = []

    # Загальний чат — доступний всім
    general_last = await _get_last_message_at(session_id, "general", None, None, db)
    chats.append(ChatListItem(
        channel="general",
        title=f"{session.name} — Загальний чат",
        last_message_at=general_last,
    ))

    if is_org:
        # Організатор: бачить чати підтримки з кожним учасником
        parts_result = await db.execute(
            select(Participant)
            .where(Participant.session_id == session_id)
            .options(selectinload(Participant.user))
        )
        for p in parts_result.scalars().all():
            support_last = await _get_last_message_at(session_id, "support", None, p.id, db)
            chats.append(ChatListItem(
                channel=f"support:{p.id}",
                title=f"{session.name} — {p.name}",
                subtitle="Підтримка",
                last_message_at=support_last,
            ))
    else:
        # Учасник: командний чат (якщо є команда) + чат підтримки
        if participant and participant.team_id:
            from app.models.team import Team
            team_result = await db.execute(
                select(Team).where(Team.id == participant.team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                team_last = await _get_last_message_at(session_id, "team", team.id, None, db)
                chats.append(ChatListItem(
                    channel=f"team:{team.id}",
                    title=f"{session.name} — {team.name}",
                    last_message_at=team_last,
                ))

        if participant:
            support_last = await _get_last_message_at(session_id, "support", None, participant.id, db)
            chats.append(ChatListItem(
                channel=f"support:{participant.id}",
                title=f"{session.name} — Підтримка",
                subtitle="Зв'язок з організаторами",
                last_message_at=support_last,
            ))

    return chats


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: UUID,
    token: str = Query(...),
    channel: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    is_org = await _is_organizer(session_id, user.id, db)
    participant = await _get_participant(session_id, user.id, db)

    # Перевірка доступу до каналу
    if channel == "general":
        pass  # всі мають доступ
    elif channel.startswith("team:"):
        if is_org:
            pass  # організатор може читати будь-який командний чат
        elif participant and str(participant.team_id) == channel.split(":")[1]:
            pass  # учасник своєї команди
        else:
            await websocket.close(code=1008)
            return
    elif channel.startswith("support:"):
        support_participant_id = channel.split(":")[1]
        if is_org:
            pass  # організатори мають доступ до всіх чатів підтримки
        elif participant and str(participant.id) == support_participant_id:
            pass  # це чат цього учасника
        else:
            await websocket.close(code=1008)
            return
    else:
        await websocket.close(code=1008)
        return

    sid = str(session_id)
    await manager.connect(websocket, sid, channel, str(user.id))

    # Надсилаємо історію
    if channel == "general":
        history = await _load_history(session_id, "general", db)
    elif channel.startswith("team:"):
        team_uuid = UUID(channel.split(":")[1])
        history = await _load_team_history(session_id, team_uuid, db)
    elif channel.startswith("support:"):
        p_id = UUID(channel.split(":")[1])
        history = await _load_support_history(session_id, p_id, db)
    else:
        history = []

    await websocket.send_json({"type": "history", "messages": history})

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            content = (data.get("content") or "").strip()
            if not content:
                continue

            # Зберігаємо повідомлення
            msg = Message(
                id=uuid.uuid4(),
                session_id=session_id,
                sender_id=user.id,
                channel="general" if channel == "general"
                        else "team" if channel.startswith("team:")
                        else "support",
                team_id=UUID(channel.split(":")[1]) if channel.startswith("team:") else None,
                participant_id=UUID(channel.split(":")[1]) if channel.startswith("support:") else None,
                content=content,
                created_at=datetime.now(timezone.utc),
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            # Завантажуємо sender для форматування
            sender_result = await db.execute(select(User).where(User.id == user.id))
            msg.sender = sender_result.scalar_one()

            payload = {"type": "message", "message": _format(msg)}

            # Розсилаємо
            if channel == "general":
                await manager.broadcast(sid, channel, payload)
            elif channel.startswith("team:"):
                await manager.broadcast(sid, channel, payload)
            elif channel.startswith("support:"):
                # Надсилаємо учаснику і всім організаторам
                await manager.broadcast(sid, channel, payload)

    except WebSocketDisconnect:
        manager.disconnect(websocket, sid, channel)
    except Exception:
        manager.disconnect(websocket, sid, channel)