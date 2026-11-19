from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import TelegramMethod
from aiogram.types import InlineKeyboardMarkup

from .formatting import strip_custom_emoji
from .keyboards import strip_icons

logger = logging.getLogger(__name__)


class SupportBot(Bot):
    """Bot с аварийным режимом для premium-эмодзи.

    Premium-эмодзи в тексте и в кнопках поддерживаются не всеми ботами
    (Telegram разрешает их не всем аккаунтам). Если API отклоняет запрос,
    повторяем его без premium-разметки, чтобы бот остался рабочим.
    """

    async def __call__(
        self,
        method: TelegramMethod[Any],
        request_timeout: int | None = None,
    ) -> Any:
        try:
            return await super().__call__(method, request_timeout)
        except TelegramBadRequest as error:
            if "message is not modified" in str(error).lower():
                raise

            updates: dict[str, Any] = {}
            reply_markup = getattr(method, "reply_markup", None)
            if isinstance(reply_markup, InlineKeyboardMarkup):
                plain_markup = strip_icons(reply_markup)
                if plain_markup is not reply_markup:
                    updates["reply_markup"] = plain_markup

            for field in ("text", "caption"):
                value = getattr(method, field, None)
                if isinstance(value, str) and "tg://emoji?id=" in value:
                    updates[field] = strip_custom_emoji(value)

            if not updates:
                raise

            logger.warning(
                "Повтор запроса без premium-эмодзи после ошибки: %s",
                error,
            )
            return await super().__call__(
                method.model_copy(update=updates),
                request_timeout,
            )
