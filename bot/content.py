from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from aiogram.types import Message

from .formatting import truncate_plain

FILE_LABELS = {
    "photo": "фото",
    "document": "документ",
    "video": "видео",
    "audio": "аудио",
    "voice": "голосовое сообщение",
    "animation": "GIF",
    "video_note": "видеосообщение",
    "sticker": "стикер",
}


@dataclass(slots=True)
class Content:
    text: str | None = None
    file_id: str | None = None
    file_type: str | None = None
    file_name: str | None = None

    @property
    def has_payload(self) -> bool:
        return bool(self.file_id or (self.text and self.text.strip()))

    @property
    def file_label(self) -> str:
        return FILE_LABELS.get(self.file_type or "", "вложение")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Content":
        return cls(
            text=data.get("text"),
            file_id=data.get("file_id"),
            file_type=data.get("file_type"),
            file_name=data.get("file_name"),
        )


def extract_content(message: Message) -> Content:
    text = message.text if message.text is not None else message.caption

    if message.photo:
        return Content(text=text, file_id=message.photo[-1].file_id, file_type="photo")
    if message.document:
        return Content(
            text=text,
            file_id=message.document.file_id,
            file_type="document",
            file_name=message.document.file_name,
        )
    if message.video:
        return Content(
            text=text,
            file_id=message.video.file_id,
            file_type="video",
            file_name=message.video.file_name,
        )
    if message.audio:
        return Content(
            text=text,
            file_id=message.audio.file_id,
            file_type="audio",
            file_name=message.audio.file_name,
        )
    if message.voice:
        return Content(text=text, file_id=message.voice.file_id, file_type="voice")
    if message.animation:
        return Content(
            text=text,
            file_id=message.animation.file_id,
            file_type="animation",
            file_name=message.animation.file_name,
        )
    if message.video_note:
        return Content(text=text, file_id=message.video_note.file_id, file_type="video_note")
    if message.sticker:
        return Content(text=text, file_id=message.sticker.file_id, file_type="sticker")

    return Content(text=text)


def preview(content: Content, limit: int = 120) -> str:
    if content.text:
        return truncate_plain(content.text, limit)
    if content.file_id:
        return f"Вложение: {content.file_label}"
    return "Без текста"
