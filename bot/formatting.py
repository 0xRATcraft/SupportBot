from __future__ import annotations

import re

from .emojis import ce, icon_id

# Спецсимволы MarkdownV2 из документации Telegram Bot API.
_MD_ESCAPE_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")
_EMOJI_MD_RE = re.compile(r"!\[([^\]]*)\]\(tg://emoji\?id=\d+\)")
_MD_UNESCAPE_RE = re.compile(r"\\([^A-Za-z0-9\s])")


def esc(value: object | None) -> str:
    """Экранировать произвольный текст для MarkdownV2."""
    if value is None:
        return ""
    return _MD_ESCAPE_RE.sub(r"\\\1", str(value))


def bold(value: object | None) -> str:
    return f"*{esc(value)}*"


def line(emoji_name: str, value: object | None) -> str:
    return f"{ce(emoji_name)} {esc(value)}"


def truncate_plain(value: str | None, limit: int = 3000) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def esc_truncate(value: str | None, limit: int = 3500) -> str:
    """Экранировать текст для MarkdownV2 и безопасно ограничить его длину.

    Экранирование может почти удвоить длину строки, поэтому ограничение
    применяется уже после него. Хвостовой escape-слэш при обрезке убирается,
    чтобы не сломать MarkdownV2.
    """
    if not value or not value.strip():
        return ""
    escaped = esc(value.strip())
    if len(escaped) <= limit:
        return escaped
    cut = escaped[:limit]
    trailing = len(cut) - len(cut.rstrip("\\"))
    if trailing % 2 == 1:
        cut = cut[:-1]
    return cut + "…"


def to_plain(value: str) -> str:
    """Убрать MarkdownV2-разметку для текстов callback-алертов."""
    without_emoji = _EMOJI_MD_RE.sub(r"\1", str(value))
    return _MD_UNESCAPE_RE.sub(r"\1", without_emoji)


def strip_custom_emoji(value: str) -> str:
    """Заменить premium-эмодзи на обычные символы (аварийный режим)."""
    return _EMOJI_MD_RE.sub(r"\1", str(value))


def short_name(name: str, username: str | None = None, limit: int = 24) -> str:
    base = (name or "").strip() or (f"@{username}" if username else "Без имени")
    if len(base) > limit:
        base = base[: max(0, limit - 1)].rstrip() + "…"
    return base


__all__ = [
    "esc",
    "bold",
    "line",
    "truncate_plain",
    "esc_truncate",
    "to_plain",
    "strip_custom_emoji",
    "short_name",
    "ce",
    "icon_id",
]
