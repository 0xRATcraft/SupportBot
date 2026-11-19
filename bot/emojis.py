from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PremiumEmoji:
    char: str
    custom_id: str


# Все ID взяты из messages.md. Новые premium-эмодзи не добавляем.
EMOJI: dict[str, PremiumEmoji] = {
    "folder": PremiumEmoji("📁", "6037475557082403885"),
    "open_folder": PremiumEmoji("📂", "6037373985400819577"),
    "cross": PremiumEmoji("❌", "5774077015388852135"),
    "back": PremiumEmoji("⬅️", "5960671702059848143"),
    "trash": PremiumEmoji("🗑", "6039522349517115015"),
    "archive_list": PremiumEmoji("🗂", "5766994197705921104"),
    "prev": PremiumEmoji("⬅️", "6039539366177541657"),
    "next": PremiumEmoji("➡️", "6037622221625626773"),
    "unarchive": PremiumEmoji("📤", "6043874504302661409"),
    "keyboard": PremiumEmoji("⌨️", "6039404727542747508"),
    "archive_in": PremiumEmoji("📥", "6039420807900303010"),
    "hourglass": PremiumEmoji("⌛️", "5891211339170326418"),
    "closed_in": PremiumEmoji("📥", "6039400853482246862"),
    "eye": PremiumEmoji("👁", "6037397706505195857"),
    "confirm": PremiumEmoji("✅", "5774022692642492953"),
    "question": PremiumEmoji("❓", "6030848053177486888"),
    "archived": PremiumEmoji("📥", "6041730074376410123"),
    "profile": PremiumEmoji("👤", "6035084557378654059"),
    "tag": PremiumEmoji("🏷", "5886285355279193209"),
    "counter": PremiumEmoji("📂", "6039348811363520645"),
    "message": PremiumEmoji("💬", "6034831751308644168"),
    "info": PremiumEmoji("ℹ️", "6028435952299413210"),
    "warning": PremiumEmoji("❗️", "6030563507299160824"),
    "chat": PremiumEmoji("💬", "6037421444789440735"),
    "bolt": PremiumEmoji("⚡️", "5920515922505765329"),
    "pencil": PremiumEmoji("✏️", "6039779802741739617"),
    "robot": PremiumEmoji("🤖", "6030400221232501136"),
}


def ce(name: str) -> str:
    """Вернуть MarkdownV2-разметку premium-эмодзи в формате Telegram."""
    emoji = EMOJI[name]
    return f"![{emoji.char}](tg://emoji?id={emoji.custom_id})"


def icon_id(name: str) -> str:
    """ID premium-эмодзи для icon_custom_emoji_id кнопки."""
    return EMOJI[name].custom_id


def emoji_char(name: str) -> str:
    return EMOJI[name].char
