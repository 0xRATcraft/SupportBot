from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

CAPTION_LIMIT = 1024


async def send_text(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    try:
        return await message.edit_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return message
        return await send_text(message.chat.id, text, reply_markup)


async def safe_delete(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    except Exception:
        pass


async def send_content(
    bot: Bot,
    chat_id: int,
    *,
    text: str,
    file_id: str | None = None,
    file_type: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> list[Message]:
    """Отправить текст и/или вложение с корректным разбиением подписи."""
    sent: list[Message] = []

    if not file_id:
        if text:
            sent.append(await send_text(bot, chat_id, text, reply_markup))
        return sent

    if file_type in {"video_note", "sticker"}:
        if text:
            sent.append(await send_text(bot, chat_id, text, reply_markup))
            reply_markup = None
        sent.append(
            await _send_media(
                bot=bot,
                chat_id=chat_id,
                file_id=file_id,
                file_type=file_type or "document",
                caption=None,
                reply_markup=reply_markup,
            )
        )
        return sent

    if text and len(text) <= CAPTION_LIMIT:
        sent.append(
            await _send_media(
                bot=bot,
                chat_id=chat_id,
                file_id=file_id,
                file_type=file_type or "document",
                caption=text,
                reply_markup=reply_markup,
            )
        )
        return sent

    if text:
        sent.append(await send_text(bot, chat_id, text, reply_markup))
        reply_markup = None
    sent.append(
        await _send_media(
            bot=bot,
            chat_id=chat_id,
            file_id=file_id,
            file_type=file_type or "document",
            caption=None,
            reply_markup=reply_markup,
        )
    )
    return sent


async def _send_media(
    *,
    bot: Bot,
    chat_id: int,
    file_id: str,
    file_type: str,
    caption: str | None,
    reply_markup: InlineKeyboardMarkup | None,
) -> Message:
    kwargs: dict[str, Any] = {"chat_id": chat_id, "reply_markup": reply_markup}
    if caption:
        kwargs["caption"] = caption
        kwargs["parse_mode"] = ParseMode.MARKDOWN_V2

    if file_type == "photo":
        return await bot.send_photo(photo=file_id, **kwargs)
    if file_type == "video":
        return await bot.send_video(video=file_id, **kwargs)
    if file_type == "animation":
        return await bot.send_animation(animation=file_id, **kwargs)
    if file_type == "audio":
        return await bot.send_audio(audio=file_id, **kwargs)
    if file_type == "voice":
        return await bot.send_voice(voice=file_id, **kwargs)
    if file_type == "video_note":
        kwargs.pop("caption", None)
        kwargs.pop("parse_mode", None)
        return await bot.send_video_note(video_note=file_id, **kwargs)
    if file_type == "sticker":
        kwargs.pop("caption", None)
        kwargs.pop("parse_mode", None)
        return await bot.send_sticker(sticker=file_id, **kwargs)
    return await bot.send_document(document=file_id, **kwargs)
