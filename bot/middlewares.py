from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from . import texts
from .db import Database
from .formatting import to_plain


def display_name(user: User) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return name or (f"@{user.username}" if user.username else str(user.id))


class AccessMiddleware(BaseMiddleware):
    def __init__(self, db: Database, admin_ids: frozenset[int]) -> None:
        self.db = db
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)

        await self.db.upsert_user(user.id, user.username, display_name(user))
        db_user = await self.db.get_user(user.id)
        data["db_user"] = db_user

        if user.id in self.admin_ids:
            return await handler(event, data)

        if db_user and db_user.get("is_blocked"):
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(texts.blocked_alert(), show_alert=True)
                except Exception:
                    pass
            elif isinstance(event, Message):
                try:
                    await event.answer(texts.blocked_user())
                except Exception:
                    pass
            return None

        return await handler(event, data)


class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: frozenset[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.id not in self.admin_ids:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(to_plain(texts.no_access()), show_alert=True)
                except Exception:
                    pass
            elif isinstance(event, Message):
                try:
                    await event.answer(texts.no_access())
                except Exception:
                    pass
            return None
        return await handler(event, data)
