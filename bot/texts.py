from __future__ import annotations

from typing import Any

from .content import Content, preview
from .formatting import bold, esc, esc_truncate, line, truncate_plain
from .emojis import ce

STATUS_LABELS = {
    "open": "Ожидает ответа оператора",
    "answered": "Оператор ответил",
    "archived": "В архиве",
    "closed": "Закрыто",
}


def main_menu(support_name: str) -> str:
    return "\n\n".join(
        [
            f"{ce('robot')} {bold(f'Добро пожаловать в бота поддержки «{support_name}»!')}",
            f"{ce('info')} "
            f"{esc('Ниже вы можете создать обращение в службу поддержки — мы обязательно вам поможем.')}",
        ]
    )


def new_ticket_prompt() -> str:
    return "\n".join(
        [
            f"{ce('pencil')} {bold('Новое обращение')}",
            f"{ce('keyboard')} "
            f"{esc('Пожалуйста, напишите ваш вопрос одним сообщением; при необходимости можете добавить вложения.')}",
            "",
            f"{ce('info')} "
            f"{esc('Дополнить обращение можно позже. Не закрывайте обращение, если вы что-то не уточнили.')}",
        ]
    )


def ticket_created(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('tag')} {bold(f'Обращение #{ticket_id} создано!')}",
            f"{ce('bolt')} "
            f"{esc('Мы уже получили уведомление — оператор постарается ответить как можно быстрее.')}",
            f"{ce('open_folder')} "
            f"{esc('Если вы вспомнили что-то важное, что может помочь с ответом, отправьте это прямо сейчас — новым сообщением.')}",
        ]
    )


def ticket_active(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('folder')} {bold(f'Обращение #{ticket_id}')}",
            f"{ce('open_folder')} "
            f"{esc('Если вы вспомнили что-то важное, что может помочь с ответом, отправьте это прямо сейчас — новым сообщением.')}",
        ]
    )


def admin_ticket(ticket: dict[str, Any], user_tickets: int) -> str:
    ticket_id = int(ticket["id"])
    user_id = int(ticket["user_id"])
    status = str(ticket["status"])
    username = ticket.get("username")
    full_name = ticket.get("full_name") or "Без имени"

    rows = [
        f"{ce('folder')} {bold(f'Обращение #{ticket_id}')}",
        f"{ce('open_folder')} "
        f"{esc('Если пользователь вспомнил что-то важное, он может отправить это новым сообщением.')}",
        "",
        f"{ce('tag')} {esc(f'ID пользователя: {user_id}')}",
        f"{ce('eye')} {esc(f'Имя: {full_name}')}",
    ]
    if username:
        rows.append(f"{ce('profile')} {esc(f'Username: @{username}')}")
    rows.extend(
        [
            f"{ce('counter')} {esc(f'Всего обращений пользователя: {user_tickets}')}",
            f"{ce('info')} {esc(f'Статус: {STATUS_LABELS.get(status, status)}')}",
        ]
    )

    if ticket.get("close_requested"):
        rows.append(
            f"{ce('warning')} {esc('Пользователю отправлено предложение закрыть обращение.')}"
        )
    if status == "archived":
        rows.append(
            f"{ce('unarchive')} "
            f"{esc('Ответ оператора разархивирует обращение и вернёт его в работу.')}"
        )
    elif status == "closed":
        rows.append(
            f"{ce('closed_in')} {esc('Обращение закрыто, отправка ответа недоступна.')}"
        )
    elif status in {"open", "answered"}:
        rows.append(
            f"{ce('keyboard')} {esc('Отправьте сообщение, чтобы ответить пользователю.')}"
        )

    return "\n".join(rows)


def archived_ticket(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('archived')} {bold(f'Архивное обращение #{ticket_id}')}",
            f"{ce('eye')} "
            f"{esc('Вы можете просмотреть историю обращения и возобновить работу над ним, если отправите ответ оператору.')}",
        ]
    )


def closed_ticket(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('closed_in')} {bold(f'Закрытое обращение #{ticket_id}')}",
            f"{ce('eye')} "
            f"{esc('Вы можете просмотреть историю обращения, но добавить новые сообщения больше нельзя.')}",
        ]
    )


def archive_menu() -> str:
    return "\n\n".join(
        [
            f"{ce('archived')} {bold('Архив обращений')}",
            f"{ce('chat')} "
            f"{esc('В этом архиве хранятся все обращения. Вы можете создать новое обращение или возобновить работу над старым, используйте кнопки ниже.')}",
        ]
    )


def archive_empty() -> str:
    return f"{ce('open_folder')} {esc('В архиве пока нет обращений.')}"


def profile(user_id: int, full_name: str, tickets_count: int) -> str:
    return "\n".join(
        [
            f"{ce('profile')} {bold('Профиль')}",
            f"{ce('tag')} {esc(f'Ваш ID: {user_id}')}",
            f"{ce('eye')} {esc(f'Ваше имя: {full_name}')}",
            f"{ce('counter')} {esc(f'Количество обращений: {tickets_count}')}",
        ]
    )


def message_sent() -> str:
    return f"{ce('info')} {esc('Ваше сообщение отправлено — оператор, ответственный за это обращение, уже может его увидеть.')}"


def offer_close() -> str:
    return "\n\n".join(
        [
            f"{ce('warning')} {esc('Оператор поддержки предложил закрыть обращение.')}",
            f"{ce('info')} "
            f"{esc('Нажмите на кнопку ниже, чтобы закрыть обращение. Доступ к нему будет по ссылке, которую выдаст бот, когда обращение будет закрыто.')}",
        ]
    )


def close_confirm() -> str:
    return "\n\n".join(
        [
            f"{ce('question')} {esc('Вы уверены, что хотите закрыть обращение?')}",
            f"{ce('eye')} "
            f"{esc('Его историю можно будет просмотреть позже, но отправка новых сообщений будет невозможна.')}",
        ]
    )


def closed_notice(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('closed_in')} {bold(f'Обращение #{ticket_id} закрыто!')}",
            f"{ce('eye')} {esc('Вы можете просмотреть историю обращения в архиве.')}",
        ]
    )


def archived_notice(ticket_id: int, hours: int = 48) -> str:
    return "\n\n".join(
        [
            f"{ce('archive_in')} {bold(f'Обращение #{ticket_id} заархивировано.')}",
            f"{ce('hourglass')} "
            f"{esc(f'Оператор не получил ответа в течение {hours} часов.')}",
            f"{ce('unarchive')} "
            f"{esc('Разархивировать обращение можно в архиве, отправив ответ оператору.')}",
        ]
    )


def unarchive_prompt(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('unarchive')} {bold(f'Разархивирование обращения #{ticket_id}')}",
            f"{ce('keyboard')} "
            f"{esc('Отправьте ответ оператору на последнее его сообщение.')}",
        ]
    )


def operator_reply(admin_name: str, text: str | None, file_type: str | None) -> str:
    rows = [f"{ce('message')} {bold(f'Ответ от оператора поддержки {admin_name}:')}"]
    clean_text = esc_truncate(text, 3500)
    if clean_text:
        rows.append(clean_text)
    if file_type:
        rows.append(f"{ce('open_folder')} {esc(f'Вложение: {_file_label(file_type)}')}")
    return "\n".join(rows)


def history_item(message: dict[str, Any]) -> str:
    sender_type = message.get("sender_type")
    sender_name = message.get("sender_name") or (
        "Оператор поддержки" if sender_type == "admin" else "Пользователь"
    )
    text = message.get("text")
    file_type = message.get("file_type")

    if sender_type == "admin":
        return operator_reply(sender_name, text, file_type)

    header = f"{ce('profile')} {bold(f'{sender_name}:')}"
    rows = [header]
    clean_text = esc_truncate(text, 3500)
    if clean_text:
        rows.append(clean_text)
    if file_type:
        rows.append(f"{ce('open_folder')} {esc(f'Вложение: {_file_label(file_type)}')}")
    if len(rows) == 1:
        rows.append(esc("Сообщение без текста"))
    return "\n".join(rows)


def history_truncated(shown: int, total: int) -> str:
    return f"{ce('info')} {esc(f'Показаны последние {shown} сообщений из {total}.')}"


def history_empty() -> str:
    return f"{ce('info')} {esc('История сообщений пока пуста.')}"


def already_active(ticket_id: int) -> str:
    return (
        f"{ce('warning')} "
        f"{esc(f'У вас уже есть активное обращение #{ticket_id}. Новое можно создать после закрытия текущего.')}"
    )


def unsupported_content() -> str:
    return f"{ce('cross')} {esc('Не удалось распознать сообщение. Отправьте текст или вложение.')}"


def ticket_not_found() -> str:
    return f"{ce('cross')} {esc('Обращение не найдено или уже удалено.')}"


def ticket_closed_error() -> str:
    return f"{ce('closed_in')} {esc('Обращение закрыто — отправка новых сообщений невозможна.')}"


def no_access() -> str:
    return f"{ce('cross')} {esc('У вас нет доступа к этому разделу.')}"


def blocked_user() -> str:
    return f"{ce('cross')} {esc('Вы заблокированы в боте поддержки. Обратитесь к администратору.')}"


def blocked_alert() -> str:
    return "Вы заблокированы в боте поддержки."


def error_message() -> str:
    return f"{ce('cross')} {esc('Произошла ошибка. Попробуйте ещё раз.')}"


def admin_panel(stats: dict[str, int]) -> str:
    users_total = stats["users_total"]
    users_blocked = stats["users_blocked"]
    active_tickets = stats["active_tickets"]
    archive_tickets = stats["archive_tickets"]
    return "\n\n".join(
        [
            f"{ce('archive_list')} {bold('Админ-панель')}",
            "\n".join(
                [
                    f"{ce('profile')} "
                    f"{esc(f'Пользователей: {users_total} (заблокировано: {users_blocked})')}",
                    f"{ce('folder')} "
                    f"{esc(f'Активных обращений: {active_tickets}')}",
                    f"{ce('archived')} "
                    f"{esc(f'В архиве: {archive_tickets}')}",
                ]
            ),
        ]
    )


def admin_tickets_title(mode: str) -> str:
    if mode == "archive":
        return f"{ce('archived')} {bold('Архив обращений')}"
    return f"{ce('archive_list')} {bold('Список обращений')}"


def admin_tickets_empty(mode: str) -> str:
    if mode == "archive":
        return archive_empty()
    return f"{ce('open_folder')} {esc('Активных обращений нет.')}"


def admin_operator_name_prompt(current: str) -> str:
    safe_current = truncate_plain(current, 100)
    return "\n\n".join(
        [
            f"{ce('profile')} {bold('Имя оператора')}",
            f"{ce('pencil')} "
            f"{esc('Отправьте имя, которое будет отображаться пользователям в ответах поддержки.')}",
            f"{ce('info')} {esc(f'Сейчас: {safe_current}')}",
        ]
    )


def admin_operator_name_invalid(limit: int = 64) -> str:
    return f"{ce('cross')} {esc(f'Отправьте имя текстом до {limit} символов.')}"


def admin_operator_name_saved(name: str) -> str:
    return "\n\n".join(
        [
            f"{ce('confirm')} {bold('Имя оператора сохранено')}",
            f"{ce('profile')} {esc(f'Пользователи увидят имя: {name}')}",
        ]
    )


def admin_search_prompt() -> str:
    return "\n\n".join(
        [
            f"{ce('profile')} {bold('Поиск пользователя')}",
            f"{ce('keyboard')} {esc('Отправьте Telegram ID или @username пользователя.')}",
        ]
    )


def admin_user_not_found(query: str) -> str:
    safe_query = truncate_plain(query, 100)
    return f"{ce('cross')} {esc(f'Пользователь {safe_query} не найден в базе бота.')}"


def admin_user_card(user: dict[str, Any], tickets_count: int) -> str:
    user_id = user["telegram_id"]
    full_name = user.get("full_name") or "Без имени"
    username = user.get("username")
    rows = [
        f"{ce('profile')} {bold('Пользователь')}",
        f"{ce('tag')} {esc(f'ID: {user_id}')}",
        f"{ce('eye')} {esc(f'Имя: {full_name}')}",
    ]
    if username:
        rows.append(f"{ce('profile')} {esc(f'Username: @{username}')}")
    rows.append(f"{ce('counter')} {esc(f'Обращений: {tickets_count}')}")
    if user.get("is_blocked"):
        rows.append(f"{ce('cross')} {esc('Статус: заблокирован')}")
    else:
        rows.append(f"{ce('confirm')} {esc('Статус: активен')}")
    return "\n".join(rows)


def admin_block_forbidden() -> str:
    return f"{ce('cross')} {esc('Нельзя заблокировать администратора бота.')}"


def admin_broadcast_prompt(count: int) -> str:
    return "\n\n".join(
        [
            f"{ce('unarchive')} {bold('Рассылка')}",
            f"{ce('keyboard')} "
            f"{esc('Отправьте сообщение для рассылки: текст, фото, видео, документ, аудио или голосовое.')}",
            f"{ce('profile')} {esc(f'Получателей: {count}')}",
        ]
    )


def admin_broadcast_preview(count: int) -> str:
    return "\n\n".join(
        [
            f"{ce('eye')} {bold('Проверьте рассылку')}",
            f"{ce('profile')} {esc(f'Получателей: {count}')}",
            f"{ce('info')} "
            f"{esc('Заблокированные пользователи и администраторы не получат сообщение.')}",
        ]
    )


def admin_broadcast_confirm_hint() -> str:
    return f"{ce('info')} {esc('Нажмите «Подтвердить» или «Отмена».')}"


def admin_broadcast_started(count: int) -> str:
    return "\n\n".join(
        [
            f"{ce('unarchive')} {bold('Рассылка запущена')}",
            f"{ce('profile')} {esc(f'Получателей: {count}')}",
            f"{ce('hourglass')} {esc('Бот отправит сообщения в фоне, отчёт придёт сюда.')}",
        ]
    )


def admin_broadcast_done(sent: int, failed: int) -> str:
    return "\n\n".join(
        [
            f"{ce('confirm')} {bold('Рассылка завершена')}",
            f"{ce('eye')} {esc(f'Доставлено: {sent}')}",
            f"{ce('cross')} {esc(f'Ошибок: {failed}')}",
        ]
    )


def admin_broadcast_cancelled() -> str:
    return f"{ce('cross')} {esc('Рассылка отменена.')}"


def admin_delete_confirm(ticket_id: int) -> str:
    return "\n\n".join(
        [
            f"{ce('question')} {bold(f'Удалить обращение #{ticket_id}?')}",
            f"{ce('warning')} "
            f"{esc('Обращение исчезнет из списков и архива пользователя. Действие необратимо.')}",
        ]
    )


def admin_deleted(ticket_id: int) -> str:
    return f"{ce('trash')} {esc(f'Обращение #{ticket_id} удалено.')}"


def user_ticket_deleted(ticket_id: int) -> str:
    return f"{ce('trash')} {esc(f'Обращение #{ticket_id} удалено оператором поддержки.')}"


def admin_reply_sent() -> str:
    return f"{ce('confirm')} {esc('Ответ отправлен пользователю.')}"


def admin_reply_failed() -> str:
    return f"{ce('cross')} {esc('Не удалось отправить ответ пользователю. Возможно, бот заблокирован.')}"


def admin_offer_sent() -> str:
    return f"{ce('confirm')} {esc('Пользователю отправлено предложение закрыть обращение.')}"


def admin_offer_failed() -> str:
    return f"{ce('cross')} {esc('Не удалось отправить предложение пользователю.')}"


def admin_new_ticket(ticket: dict[str, Any], content: Content) -> str:
    ticket_id = ticket["id"]
    user_id = ticket["user_id"]
    username = ticket.get("username")
    name = ticket.get("full_name") or "Без имени"
    author = f"{name} (@{username})" if username else name
    return "\n\n".join(
        [
            f"{ce('folder')} {bold(f'Новое обращение #{ticket_id}')}",
            f"{ce('profile')} {esc(author)}",
            f"{ce('tag')} {esc(f'ID: {user_id}')}",
            f"{ce('chat')} {esc(preview(content))}",
            f"{ce('keyboard')} {esc('Откройте обращение, чтобы ответить пользователю.')}",
        ]
    )


def admin_new_message(ticket: dict[str, Any], content: Content) -> str:
    ticket_id = ticket["id"]
    username = ticket.get("username")
    name = ticket.get("full_name") or "Без имени"
    author = f"{name} (@{username})" if username else name
    return "\n\n".join(
        [
            f"{ce('message')} {bold(f'Новое сообщение в обращении #{ticket_id}')}",
            f"{ce('profile')} {esc(author)}",
            f"{ce('chat')} {esc(preview(content))}",
        ]
    )


def admin_user_closed(ticket_id: int) -> str:
    return f"{ce('closed_in')} {esc(f'Пользователь закрыл обращение #{ticket_id}.')}"


def broadcast_message(text: str | None, file_type: str | None, support_name: str) -> str:
    rows = [f"{ce('unarchive')} {bold(f'Рассылка от поддержки «{support_name}»')}", ""]
    if text:
        rows.append(esc_truncate(text, 3500))
    if file_type:
        rows.append(f"{ce('open_folder')} {esc(f'Вложение: {_file_label(file_type)}')}")
    rows.extend(
        [
            "",
            f"{ce('info')} {esc('Если у вас есть вопросы — создайте обращение в меню бота.')}",
        ]
    )
    return "\n".join(rows)


def _file_label(file_type: str) -> str:
    labels = {
        "photo": "фото",
        "document": "документ",
        "video": "видео",
        "audio": "аудио",
        "voice": "голосовое сообщение",
        "animation": "GIF",
        "video_note": "видеосообщение",
        "sticker": "стикер",
    }
    return labels.get(file_type, "вложение")
