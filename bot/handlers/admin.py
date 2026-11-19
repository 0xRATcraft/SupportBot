from __future__ import annotations

from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from .. import services, texts
from ..config import Config
from ..content import Content, extract_content
from ..db import Database
from ..formatting import to_plain
from ..middlewares import display_name
from ..sending import edit_text, send_content, send_text

router = Router(name="admin")

MAX_OPERATOR_NAME = 64


class AdminStates(StatesGroup):
    ticket_reply = State()
    broadcast = State()
    broadcast_confirm = State()
    user_search = State()
    operator_name = State()


async def _show_panel(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    stats = await db.get_stats()
    await message.answer(
        texts.admin_panel(stats),
        reply_markup=kb.admin_menu(),
    )


@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    await _show_panel(message, state, db)


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    await _show_panel(message, state, db)


@router.callback_query(F.data == "admin:menu")
async def cb_menu(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    stats = await db.get_stats()
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_panel(stats),
        kb.admin_menu(),
    )


@router.callback_query(F.data.startswith("admin:tickets:"))
async def cb_tickets(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 4:
        await callback.answer("Некорректная страница.", show_alert=True)
        return
    mode = parts[2] if parts[2] in {"active", "archive"} else "active"
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0

    tickets, total, pages = await db.get_admin_tickets(mode, page)
    if page >= pages:
        page = pages - 1
        tickets, total, pages = await db.get_admin_tickets(mode, page)

    text = texts.admin_tickets_title(mode)
    if not tickets:
        text = f"{text}\n\n{texts.admin_tickets_empty(mode)}"

    await callback.answer()
    await edit_text(
        callback.message,
        text,
        kb.admin_tickets(tickets, mode, page, pages),
    )


@router.callback_query(F.data.startswith("admin:ticket:"))
async def cb_ticket(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    await state.clear()
    await db.mark_admin_read(ticket_id)
    status = ticket["status"]
    if status != "closed":
        await state.set_state(AdminStates.ticket_reply)
        await state.update_data(ticket_id=ticket_id)

    await callback.answer()
    await services.show_ticket_view(
        bot,
        callback.message.chat.id,
        db,
        ticket,
        view="admin",
        edit_message=callback.message,
    )


@router.callback_query(F.data.startswith("admin:delete:"))
async def cb_delete(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_delete_confirm(ticket_id),
        kb.admin_delete_confirm(ticket_id),
    )


@router.callback_query(F.data.startswith("admin:delete_confirm:"))
async def cb_delete_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.soft_delete_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Обращение уже удалено.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_deleted(ticket_id),
        kb.admin_cancel_to_menu(),
    )
    await services.notify_user_deleted(
        bot,
        int(ticket["user_id"]),
        ticket_id,
    )


@router.callback_query(F.data.startswith("admin:delete_cancel:"))
async def cb_delete_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    await state.clear()
    if ticket["status"] != "closed":
        await state.set_state(AdminStates.ticket_reply)
        await state.update_data(ticket_id=ticket_id)
    await callback.answer()
    await services.show_ticket_view(
        bot,
        callback.message.chat.id,
        db,
        ticket,
        view="admin",
        edit_message=callback.message,
    )


@router.callback_query(F.data.startswith("admin:offer_close:"))
async def cb_offer_close(
    callback: CallbackQuery,
    db: Database,
    bot: Bot,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if ticket["status"] not in {"open", "answered"}:
        await callback.answer("Обращение недоступно для этого действия.", show_alert=True)
        return

    await db.set_close_requested(ticket_id, True)
    sent = await services.notify_user_offer_close(
        bot,
        int(ticket["user_id"]),
        ticket_id,
    )
    if not sent:
        await db.set_close_requested(ticket_id, False)
        await callback.answer("Не удалось отправить предложение.", show_alert=True)
        return
    await callback.answer("Предложение отправлено пользователю.")


@router.callback_query(F.data == "admin:users")
async def cb_users(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(AdminStates.user_search)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_search_prompt(),
        kb.admin_cancel_to_menu(),
    )


@router.callback_query(F.data == "admin:operator_name")
async def cb_operator_name(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user: dict[str, Any] | None = None,
) -> None:
    await state.set_state(AdminStates.operator_name)
    current = await db.get_operator_name(callback.from_user.id)
    if not current:
        current = (db_user or {}).get("full_name") or display_name(callback.from_user)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_operator_name_prompt(str(current)),
        kb.admin_cancel_to_menu(),
    )


@router.callback_query(F.data.startswith("admin:block:"))
async def cb_block(
    callback: CallbackQuery,
    db: Database,
    config: Config,
) -> None:
    await _toggle_block(callback, db, config, blocked=True)


@router.callback_query(F.data.startswith("admin:unblock:"))
async def cb_unblock(
    callback: CallbackQuery,
    db: Database,
    config: Config,
) -> None:
    await _toggle_block(callback, db, config, blocked=False)


async def _toggle_block(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    *,
    blocked: bool,
) -> None:
    user_id = _parse_id(callback.data, 2)
    if user_id is None:
        await callback.answer("Некорректный пользователь.", show_alert=True)
        return
    if user_id in config.admin_ids:
        await callback.answer(to_plain(texts.admin_block_forbidden()), show_alert=True)
        return
    user = await db.get_user(user_id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    await db.set_user_blocked(user_id, blocked)
    user = await db.get_user(user_id)
    count = await db.count_user_tickets(user_id)
    await callback.answer("Готово.")
    await edit_text(
        callback.message,
        texts.admin_user_card(user or {}, count),
        kb.admin_user_card(user or {}),
    )


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await state.clear()
    recipients = await services.broadcast_recipient_ids(db, config)
    await state.set_state(AdminStates.broadcast)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_broadcast_prompt(len(recipients)),
        kb.admin_cancel_to_menu(),
    )


@router.callback_query(F.data == "admin:broadcast_confirm")
async def cb_broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
) -> None:
    data = await state.get_data()
    raw_content = data.get("broadcast_content")
    if not isinstance(raw_content, dict):
        await callback.answer("Черновик рассылки потерян.", show_alert=True)
        return
    content = Content.from_dict(raw_content)
    recipients = await services.broadcast_recipient_ids(db, config)
    await state.clear()
    await callback.answer("Рассылка запущена.")
    await edit_text(
        callback.message,
        texts.admin_broadcast_started(len(recipients)),
        kb.admin_cancel_to_menu(),
    )
    services.schedule_broadcast(
        bot,
        db,
        config,
        callback.from_user.id,
        content,
    )


@router.callback_query(F.data == "admin:broadcast_cancel")
async def cb_broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()
    await edit_text(
        callback.message,
        texts.admin_broadcast_cancelled(),
        kb.admin_cancel_to_menu(),
    )


@router.message(AdminStates.ticket_reply)
async def admin_reply(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
    db_user: dict[str, Any] | None = None,
) -> None:
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    if not isinstance(ticket_id, int):
        await state.clear()
        await message.answer(texts.ticket_not_found())
        return

    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await state.clear()
        await message.answer(texts.ticket_not_found())
        return
    if ticket["status"] == "closed":
        await state.clear()
        await message.answer(texts.ticket_closed_error())
        return

    content = extract_content(message)
    if not content.has_payload:
        await message.answer(texts.unsupported_content())
        return

    custom_name = await db.get_operator_name(message.from_user.id)
    if custom_name:
        admin_name = custom_name
    elif db_user and db_user.get("full_name"):
        admin_name = str(db_user["full_name"])
    else:
        admin_name = display_name(message.from_user)

    result = await db.add_message(
        ticket_id,
        message.from_user.id,
        "admin",
        admin_name,
        content,
    )
    if result is None:
        await message.answer(texts.ticket_closed_error())
        return

    sent = await services.notify_user_operator_reply(
        bot,
        int(ticket["user_id"]),
        admin_name,
        content,
    )
    await message.answer(
        texts.admin_reply_sent() if sent else texts.admin_reply_failed()
    )


@router.message(AdminStates.user_search)
async def admin_user_search(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer(
            texts.unsupported_content(),
            reply_markup=kb.admin_cancel_to_menu(),
        )
        return

    user = await db.find_user(query)
    if user is None:
        await message.answer(
            texts.admin_user_not_found(query),
            reply_markup=kb.admin_cancel_to_menu(),
        )
        return

    await state.clear()
    count = await db.count_user_tickets(int(user["telegram_id"]))
    await message.answer(
        texts.admin_user_card(user, count),
        reply_markup=kb.admin_user_card(user),
    )


@router.message(AdminStates.broadcast)
async def admin_broadcast_content(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
) -> None:
    content = extract_content(message)
    if not content.has_payload:
        await message.answer(texts.unsupported_content())
        return

    recipients = await services.broadcast_recipient_ids(db, config)
    await state.set_state(AdminStates.broadcast_confirm)
    await state.update_data(broadcast_content=content.to_dict())

    preview = texts.broadcast_message(
        content.text,
        content.file_type,
        config.support_name,
    )
    await send_content(
        bot,
        message.chat.id,
        text=preview,
        file_id=content.file_id,
        file_type=content.file_type,
    )
    await send_text(
        bot,
        message.chat.id,
        texts.admin_broadcast_preview(len(recipients)),
        kb.broadcast_confirm(),
    )


@router.message(AdminStates.broadcast_confirm)
async def admin_broadcast_confirm_wait(
    message: Message,
) -> None:
    await message.answer(
        texts.admin_broadcast_confirm_hint(),
        reply_markup=kb.broadcast_confirm(),
    )


@router.message(AdminStates.operator_name)
async def admin_operator_name(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    name = " ".join((message.text or "").split()).strip()
    if not name or len(name) > MAX_OPERATOR_NAME:
        await message.answer(
            texts.admin_operator_name_invalid(MAX_OPERATOR_NAME),
            reply_markup=kb.admin_cancel_to_menu(),
        )
        return

    await db.set_operator_name(message.from_user.id, name)
    await state.clear()
    await message.answer(
        texts.admin_operator_name_saved(name),
        reply_markup=kb.admin_cancel_to_menu(),
    )


@router.message()
async def admin_fallback(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    await _show_panel(message, state, db)


@router.callback_query()
async def admin_unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Кнопка устарела. Откройте меню заново.")


def _parse_id(data: str | None, index: int) -> int | None:
    if not data:
        return None
    parts = data.split(":")
    if len(parts) <= index:
        return None
    try:
        return int(parts[index])
    except ValueError:
        return None
