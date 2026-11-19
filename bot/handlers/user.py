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
from ..sending import edit_text, send_text

router = Router(name="user")


class UserStates(StatesGroup):
    new_ticket = State()
    archived_reply = State()


def _sender_name(message: Message, db_user: dict[str, Any] | None) -> str:
    if db_user and db_user.get("full_name"):
        return str(db_user["full_name"])
    return display_name(message.from_user) if message.from_user else "Пользователь"


async def _active_ticket(db: Database, user_id: int) -> dict[str, Any] | None:
    return await db.get_active_ticket(user_id)


async def _show_main_for_message(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await state.clear()
    active = await _active_ticket(db, message.from_user.id)
    await message.answer(
        texts.main_menu(config.support_name),
        reply_markup=kb.user_main_menu(active is not None),
    )


@router.message(Command("start", "menu"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await _show_main_for_message(message, state, db, config)


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await _show_main_for_message(message, state, db, config)


@router.message(F.text.startswith("/"))
async def unknown_command(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await _show_main_for_message(message, state, db, config)


@router.callback_query(F.data == "user:menu")
async def cb_menu(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    await callback.answer()
    await state.clear()
    active = await _active_ticket(db, callback.from_user.id)
    await edit_text(
        callback.message,
        texts.main_menu(config.support_name),
        kb.user_main_menu(active is not None),
    )


@router.callback_query(F.data == "user:new")
async def cb_new_ticket(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    active = await _active_ticket(db, callback.from_user.id)
    if active is not None:
        await callback.answer()
        await edit_text(
            callback.message,
            texts.already_active(int(active["id"])),
            kb.user_main_menu(True),
        )
        return

    await callback.answer()
    await state.set_state(UserStates.new_ticket)
    await edit_text(
        callback.message,
        texts.new_ticket_prompt(),
        kb.new_ticket_cancel(),
    )


@router.callback_query(F.data == "user:current")
async def cb_current_ticket(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    await state.clear()
    active = await _active_ticket(db, callback.from_user.id)
    if active is None:
        await callback.answer("Активного обращения нет.", show_alert=True)
        return
    await callback.answer()
    ticket = await db.get_ticket(int(active["id"]))
    if ticket is None:
        await edit_text(callback.message, texts.ticket_not_found())
        return
    await services.show_ticket_view(
        bot,
        callback.message.chat.id,
        db,
        ticket,
        view="current",
        edit_message=callback.message,
    )


@router.callback_query(F.data == "user:profile")
async def cb_profile(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return
    count = await db.count_user_tickets(callback.from_user.id)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.profile(
            int(user["telegram_id"]),
            str(user.get("full_name") or "Без имени"),
            count,
        ),
        kb.profile_back(),
    )


@router.callback_query(F.data.startswith("user:archive:"))
async def cb_archive(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    page = _parse_page(callback.data, 2)
    tickets, total, pages = await db.get_user_archive(callback.from_user.id, page)
    if page >= pages:
        page = pages - 1
        tickets, total, pages = await db.get_user_archive(
            callback.from_user.id, page
        )
    text = texts.archive_menu()
    if not tickets:
        text = f"{text}\n\n{texts.archive_empty()}"
    await callback.answer()
    await edit_text(
        callback.message,
        text,
        kb.user_archive(tickets, page, pages),
    )


@router.callback_query(F.data.startswith("user:archive_ticket:"))
async def cb_archive_ticket(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer()
        await edit_text(callback.message, texts.ticket_not_found())
        return
    status = ticket["status"]
    if status == "archived":
        view = "archived"
    elif status == "closed":
        view = "closed"
    else:
        view = "current"
    await callback.answer()
    await services.show_ticket_view(
        bot,
        callback.message.chat.id,
        db,
        ticket,
        view=view,
        edit_message=callback.message,
    )
    if view == "closed":
        # История уходит отдельными сообщениями и уводит кнопки наверх,
        # поэтому после закрытого обращения дублируем меню внизу чата.
        active = await _active_ticket(db, callback.from_user.id)
        await send_text(
            bot,
            callback.message.chat.id,
            texts.main_menu(config.support_name),
            kb.user_main_menu(active is not None),
        )


@router.callback_query(F.data.startswith("user:unarchive:"))
async def cb_unarchive(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None or ticket["status"] != "archived":
        await callback.answer("Обращение недоступно.", show_alert=True)
        return
    active = await _active_ticket(db, callback.from_user.id)
    if active is not None:
        await callback.answer(
            to_plain(texts.already_active(int(active["id"]))),
            show_alert=True,
        )
        return
    await state.set_state(UserStates.archived_reply)
    await state.update_data(ticket_id=ticket_id)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.unarchive_prompt(ticket_id),
        kb.user_unarchive_prompt(ticket_id),
    )


@router.callback_query(F.data.startswith("user:unarchive_cancel:"))
async def cb_unarchive_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.archived_ticket(ticket_id),
        kb.user_archived_ticket(ticket_id),
    )


@router.callback_query(F.data.startswith("user:close:"))
async def cb_close(
    callback: CallbackQuery,
    db: Database,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None or ticket["status"] not in {"open", "answered"}:
        await callback.answer("Обращение недоступно.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.close_confirm(),
        kb.close_confirm(ticket_id),
    )


@router.callback_query(F.data.startswith("user:close_cancel:"))
async def cb_close_cancel(
    callback: CallbackQuery,
    db: Database,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.ticket_active(ticket_id),
        kb.user_ticket(ticket_id),
    )


@router.callback_query(F.data.startswith("user:close_confirm:"))
async def cb_close_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if ticket["status"] not in {"open", "answered"}:
        await callback.answer("Обращение уже недоступно.", show_alert=True)
        return
    if not await db.close_ticket(ticket_id):
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.closed_notice(ticket_id),
        kb.user_main_menu(False),
    )
    if config.admin_ids:
        await services.notify_admins_closed(bot, config, ticket_id)


@router.callback_query(F.data.startswith("user:offer_confirm:"))
async def cb_offer_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
) -> None:
    await state.clear()
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if ticket["status"] not in {"open", "answered"}:
        await callback.answer("Обращение уже недоступно.", show_alert=True)
        return
    if not await db.close_ticket(ticket_id):
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    await callback.answer()
    await edit_text(
        callback.message,
        texts.closed_notice(ticket_id),
        kb.user_main_menu(False),
    )
    if config.admin_ids:
        await services.notify_admins_closed(bot, config, ticket_id)


@router.callback_query(F.data.startswith("user:offer_cancel:"))
async def cb_offer_cancel(
    callback: CallbackQuery,
    db: Database,
) -> None:
    ticket_id = _parse_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer("Некорректное обращение.", show_alert=True)
        return
    ticket = await db.get_ticket_for_user(ticket_id, callback.from_user.id)
    if ticket is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if ticket["status"] not in {"open", "answered"}:
        await callback.answer("Обращение уже недоступно.", show_alert=True)
        return
    await db.set_close_requested(ticket_id, False)
    await callback.answer()
    await edit_text(
        callback.message,
        texts.ticket_active(ticket_id),
        kb.user_ticket(ticket_id),
    )


@router.message(UserStates.new_ticket)
async def create_ticket(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
    db_user: dict[str, Any] | None = None,
) -> None:
    content = extract_content(message)
    if not content.has_payload:
        await message.answer(texts.unsupported_content())
        return

    active = await _active_ticket(db, message.from_user.id)
    if active is not None:
        await state.clear()
        await message.answer(
            texts.already_active(int(active["id"])),
            reply_markup=kb.user_main_menu(True),
        )
        return

    sender = _sender_name(message, db_user)
    ticket_id = await db.create_ticket_with_message(
        message.from_user.id,
        sender,
        content,
    )
    await state.clear()
    await message.answer(
        texts.ticket_created(ticket_id),
        reply_markup=kb.user_ticket(ticket_id),
    )
    await services.notify_new_ticket(bot, db, config, ticket_id, content)


@router.message(UserStates.archived_reply)
async def reply_archived(
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

    ticket = await db.get_ticket_for_user(ticket_id, message.from_user.id)
    if ticket is None:
        await state.clear()
        await message.answer(texts.ticket_not_found())
        return
    if ticket["status"] == "closed":
        await state.clear()
        await message.answer(texts.ticket_closed_error())
        return

    active = await _active_ticket(db, message.from_user.id)
    if active is not None and int(active["id"]) != ticket_id:
        await state.clear()
        await message.answer(
            texts.already_active(int(active["id"])),
            reply_markup=kb.user_main_menu(True),
        )
        return

    content = extract_content(message)
    if not content.has_payload:
        await message.answer(texts.unsupported_content())
        return

    result = await db.add_message(
        ticket_id,
        message.from_user.id,
        "user",
        _sender_name(message, db_user),
        content,
    )
    if result is None:
        await state.clear()
        await message.answer(texts.ticket_closed_error())
        return

    await state.clear()
    await message.answer(texts.message_sent())
    await message.answer(
        texts.ticket_active(ticket_id),
        reply_markup=kb.user_ticket(ticket_id),
    )
    await services.notify_new_message(bot, db, config, ticket_id, content)


@router.message()
async def handle_user_message(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
    db_user: dict[str, Any] | None = None,
) -> None:
    active = await _active_ticket(db, message.from_user.id)
    if active is None:
        await _show_main_for_message(message, state, db, config)
        return

    content = extract_content(message)
    if not content.has_payload:
        await message.answer(texts.unsupported_content())
        return

    result = await db.add_message(
        int(active["id"]),
        message.from_user.id,
        "user",
        _sender_name(message, db_user),
        content,
    )
    if result is None:
        await message.answer(texts.ticket_closed_error())
        return

    await message.answer(texts.message_sent())
    await services.notify_new_message(
        bot,
        db,
        config,
        int(active["id"]),
        content,
    )


@router.callback_query(F.data.startswith("admin:"))
async def forbidden_admin_callback(callback: CallbackQuery) -> None:
    await callback.answer("У вас нет доступа.", show_alert=True)


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Кнопка устарела. Откройте меню заново.")


def _parse_page(data: str | None, index: int) -> int:
    if not data:
        return 0
    parts = data.split(":")
    if len(parts) <= index:
        return 0
    try:
        return max(0, int(parts[index]))
    except ValueError:
        return 0


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
