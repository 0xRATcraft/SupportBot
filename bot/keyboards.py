from __future__ import annotations

from typing import Any, Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .emojis import icon_id
from .formatting import short_name


def _btn(
    text: str,
    data: str,
    icon: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=data,
        icon_custom_emoji_id=icon_id(icon) if icon else None,
    )


def strip_icons(
    markup: InlineKeyboardMarkup | None,
) -> InlineKeyboardMarkup | None:
    """Убрать premium-иконки из кнопок, если Telegram их не принимает."""
    if markup is None:
        return None
    if not any(
        button.icon_custom_emoji_id
        for row in markup.inline_keyboard
        for button in row
    ):
        return markup
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button.model_copy(update={"icon_custom_emoji_id": None})
                for button in row
            ]
            for row in markup.inline_keyboard
        ]
    )


def _page_rows(
    page: int, pages: int, prefix: str
) -> list[list[InlineKeyboardButton]]:
    prev_data = f"{prefix}:{page - 1}" if page > 0 else "noop"
    next_data = f"{prefix}:{page + 1}" if page + 1 < pages else "noop"
    return [
        [
            _btn("Назад", prev_data, "prev"),
            _btn("Далее", next_data, "next"),
        ],
        [_btn(f"{page + 1}/{pages}", "noop")],
    ]


def user_main_menu(has_active_ticket: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [_btn("Новое обращение", "user:new", "pencil")],
    ]
    if has_active_ticket:
        rows.append([_btn("Текущее обращение", "user:current", "folder")])
    rows.append(
        [
            _btn("Архив", "user:archive:0", "archived"),
            _btn("Профиль", "user:profile", "profile"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def new_ticket_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("Отмена", "user:menu", "cross")]]
    )


def user_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Закрыть обращение", f"user:close:{ticket_id}", "cross")],
            [_btn("В меню", "user:menu", "back")],
        ]
    )


def close_confirm(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("Подтвердить", f"user:close_confirm:{ticket_id}", "confirm"),
                _btn("Отмена", f"user:close_cancel:{ticket_id}", "cross"),
            ]
        ]
    )


def offer_close(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("Подтвердить", f"user:offer_confirm:{ticket_id}", "confirm"),
                _btn("Отмена", f"user:offer_cancel:{ticket_id}", "cross"),
            ]
        ]
    )


def user_archive(
    tickets: Iterable[dict[str, Any]], page: int, pages: int
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ticket in tickets:
        status = ticket["status"]
        icon = "archived" if status == "archived" else "closed_in"
        marker = "в архиве" if status == "archived" else "закрыто"
        name = short_name(ticket.get("full_name") or "", ticket.get("username"), 18)
        rows.append(
            [
                _btn(
                    f"#{ticket['id']} · {name} · {marker}",
                    f"user:archive_ticket:{ticket['id']}",
                    icon,
                )
            ]
        )
    if pages > 1:
        rows.extend(_page_rows(page, pages, "user:archive"))
    rows.append([_btn("Назад", "user:menu", "back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_archived_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Ответить", f"user:unarchive:{ticket_id}", "pencil")],
            [_btn("Назад", "user:archive:0", "back")],
        ]
    )


def user_closed_ticket() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("Назад", "user:archive:0", "back")]]
    )


def user_unarchive_prompt(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Отмена", f"user:unarchive_cancel:{ticket_id}", "cross")]
        ]
    )


def profile_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("Назад", "user:menu", "back")]]
    )


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("Обращения", "admin:tickets:active:0", "archive_list"),
                _btn("Архив", "admin:tickets:archive:0", "archived"),
            ],
            [
                _btn("Рассылка", "admin:broadcast", "unarchive"),
                _btn("Пользователи", "admin:users", "profile"),
            ],
            [_btn("Имя оператора", "admin:operator_name", "pencil")],
        ]
    )


def admin_tickets(
    tickets: Iterable[dict[str, Any]], mode: str, page: int, pages: int
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ticket in tickets:
        status = ticket["status"]
        if ticket.get("admin_unread") and mode == "active":
            marker = "🔴"
            icon = "message"
        elif ticket.get("close_requested"):
            marker = "🟡"
            icon = "warning"
        elif status == "answered":
            marker = "🟢"
            icon = "chat"
        elif status == "archived":
            marker = "📥"
            icon = "archived"
        elif status == "closed":
            marker = "📥"
            icon = "closed_in"
        else:
            marker = "⚪"
            icon = "folder"
        name = short_name(ticket.get("full_name") or "", ticket.get("username"), 18)
        rows.append(
            [
                _btn(
                    f"#{ticket['id']} · {name} · {marker}",
                    f"admin:ticket:{ticket['id']}",
                    icon,
                )
            ]
        )
    if pages > 1:
        rows.extend(_page_rows(page, pages, f"admin:tickets:{mode}"))
    rows.append([_btn("В меню", "admin:menu", "back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_ticket(ticket: dict[str, Any]) -> InlineKeyboardMarkup:
    ticket_id = int(ticket["id"])
    status = ticket["status"]
    rows: list[list[InlineKeyboardButton]] = []
    if status in {"open", "answered"}:
        rows.append(
            [
                _btn("Удалить", f"admin:delete:{ticket_id}", "trash"),
                _btn("Пред. закрыть", f"admin:offer_close:{ticket_id}", "cross"),
            ]
        )
    else:
        rows.append([_btn("Удалить", f"admin:delete:{ticket_id}", "trash")])
    if status in {"archived", "closed"}:
        back_data = "admin:tickets:archive:0"
    else:
        back_data = "admin:tickets:active:0"
    rows.append([_btn("В список", back_data, "back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_delete_confirm(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("Подтвердить", f"admin:delete_confirm:{ticket_id}", "confirm"),
                _btn("Отмена", f"admin:delete_cancel:{ticket_id}", "cross"),
            ]
        ]
    )


def admin_user_card(user: dict[str, Any]) -> InlineKeyboardMarkup:
    user_id = int(user["telegram_id"])
    if user.get("is_blocked"):
        action = _btn("Разблокировать", f"admin:unblock:{user_id}", "confirm")
    else:
        action = _btn("Заблокировать", f"admin:block:{user_id}", "cross")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [action],
            [_btn("В меню", "admin:menu", "back")],
        ]
    )


def admin_cancel_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("В меню", "admin:menu", "back")]]
    )


def broadcast_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn("Подтвердить", "admin:broadcast_confirm", "confirm"),
                _btn("Отмена", "admin:broadcast_cancel", "cross"),
            ]
        ]
    )


def open_admin_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Открыть обращение", f"admin:ticket:{ticket_id}", "folder")]
        ]
    )
