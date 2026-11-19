from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from . import keyboards as kb
from . import texts
from .config import Config
from .content import Content
from .db import Database
from .sending import edit_text, send_content, send_text

logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task[Any]] = set()


async def send_ticket_history(
    bot: Bot,
    chat_id: int,
    db: Database,
    ticket_id: int,
    limit: int = 50,
) -> None:
    messages, total = await db.get_messages(ticket_id, limit=limit)
    if total > len(messages):
        await send_text(bot, chat_id, texts.history_truncated(len(messages), total))
    if not messages:
        await send_text(bot, chat_id, texts.history_empty())
        return

    for message in messages:
        text = texts.history_item(message)
        await send_content(
            bot,
            chat_id,
            text=text,
            file_id=message.get("file_id"),
            file_type=message.get("file_type"),
        )
        await asyncio.sleep(0)


async def show_ticket_view(
    bot: Bot,
    chat_id: int,
    db: Database,
    ticket: dict[str, Any],
    *,
    view: str,
    edit_message: Any | None = None,
) -> None:
    ticket_id = int(ticket["id"])
    if view == "admin":
        user_tickets = await db.count_user_tickets(int(ticket["user_id"]))
        header = texts.admin_ticket(ticket, user_tickets)
        markup = kb.admin_ticket(ticket)
    elif view == "archived":
        header = texts.archived_ticket(ticket_id)
        markup = kb.user_archived_ticket(ticket_id)
    elif view == "closed":
        header = texts.closed_ticket(ticket_id)
        markup = kb.user_closed_ticket()
    else:
        header = texts.ticket_active(ticket_id)
        markup = kb.user_ticket(ticket_id)

    if edit_message is not None:
        await edit_text(edit_message, header, markup)
    else:
        await send_text(bot, chat_id, header, markup)

    await send_ticket_history(bot, chat_id, db, ticket_id)


async def _send_admins(
    bot: Bot,
    config: Config,
    text: str,
    markup: Any | None = None,
) -> None:
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                text,
                parse_mode="MarkdownV2",
                reply_markup=markup,
            )
        except TelegramAPIError:
            logger.warning("Не удалось отправить уведомление админу %s", admin_id)


async def notify_new_ticket(
    bot: Bot,
    db: Database,
    config: Config,
    ticket_id: int,
    content: Content,
) -> None:
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        return
    await _send_admins(
        bot,
        config,
        texts.admin_new_ticket(ticket, content),
        kb.open_admin_ticket(ticket_id),
    )


async def notify_new_message(
    bot: Bot,
    db: Database,
    config: Config,
    ticket_id: int,
    content: Content,
) -> None:
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        return
    await _send_admins(
        bot,
        config,
        texts.admin_new_message(ticket, content),
        kb.open_admin_ticket(ticket_id),
    )


async def notify_admins_closed(
    bot: Bot,
    config: Config,
    ticket_id: int,
) -> None:
    await _send_admins(
        bot,
        config,
        texts.admin_user_closed(ticket_id),
        kb.open_admin_ticket(ticket_id),
    )


async def notify_user_operator_reply(
    bot: Bot,
    user_id: int,
    admin_name: str,
    content: Content,
) -> bool:
    text = texts.operator_reply(admin_name, content.text, content.file_type)
    try:
        await send_content(
            bot,
            user_id,
            text=text,
            file_id=content.file_id,
            file_type=content.file_type,
        )
        return True
    except TelegramAPIError:
        logger.warning("Не удалось отправить ответ пользователю %s", user_id)
        return False


async def notify_user_offer_close(bot: Bot, user_id: int, ticket_id: int) -> bool:
    try:
        await send_text(
            bot,
            user_id,
            texts.offer_close(),
            kb.offer_close(ticket_id),
        )
        return True
    except TelegramAPIError:
        return False


async def notify_user_closed(bot: Bot, user_id: int, ticket_id: int) -> bool:
    try:
        await send_text(
            bot,
            user_id,
            texts.closed_notice(ticket_id),
            kb.user_main_menu(False),
        )
        return True
    except TelegramAPIError:
        return False


async def notify_user_archived(
    bot: Bot,
    user_id: int,
    ticket_id: int,
    hours: int = 48,
) -> bool:
    try:
        await send_text(
            bot,
            user_id,
            texts.archived_notice(ticket_id, hours),
            kb.user_main_menu(False),
        )
        return True
    except TelegramAPIError:
        return False


async def notify_user_deleted(bot: Bot, user_id: int, ticket_id: int) -> bool:
    try:
        await send_text(
            bot,
            user_id,
            texts.user_ticket_deleted(ticket_id),
            kb.user_main_menu(False),
        )
        return True
    except TelegramAPIError:
        return False


async def broadcast_recipient_ids(db: Database, config: Config) -> list[int]:
    user_ids = await db.get_broadcast_user_ids()
    return [user_id for user_id in user_ids if user_id not in config.admin_ids]


def schedule_broadcast(
    bot: Bot,
    db: Database,
    config: Config,
    admin_chat_id: int,
    content: Content,
) -> None:
    task = asyncio.create_task(
        _run_broadcast(bot, db, config, admin_chat_id, content)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _run_broadcast(
    bot: Bot,
    db: Database,
    config: Config,
    admin_chat_id: int,
    content: Content,
) -> None:
    user_ids = await broadcast_recipient_ids(db, config)
    text = texts.broadcast_message(content.text, content.file_type, config.support_name)
    sent = 0
    failed = 0

    for user_id in user_ids:
        for attempt in range(2):
            try:
                await send_content(
                    bot,
                    user_id,
                    text=text,
                    file_id=content.file_id,
                    file_type=content.file_type,
                )
                sent += 1
                break
            except TelegramRetryAfter as error:
                if attempt == 0:
                    await asyncio.sleep(error.retry_after + 1)
                    continue
                failed += 1
                break
            except TelegramAPIError:
                failed += 1
                break
            except Exception:
                logger.exception("Неожиданная ошибка рассылки для %s", user_id)
                failed += 1
                break

        if config.broadcast_delay:
            await asyncio.sleep(config.broadcast_delay)

    try:
        await send_text(
            bot,
            admin_chat_id,
            texts.admin_broadcast_done(sent, failed),
            kb.admin_cancel_to_menu(),
        )
    except TelegramAPIError:
        logger.warning("Не удалось отправить отчёт о рассылке администратору")
