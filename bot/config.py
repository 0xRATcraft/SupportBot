from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    support_name: str
    db_path: Path
    archive_after_hours: int
    broadcast_delay: float
    log_level: str

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def _parse_admin_ids(raw: str) -> frozenset[int]:
    result: set[int] = set()
    for part in raw.replace(";", ",").replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            continue
    return frozenset(result)


def _parse_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _parse_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or "ReplaceMe" in token:
        raise RuntimeError(
            "Укажите реальный BOT_TOKEN в файле .env (токен можно получить у @BotFather)."
        )

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    if not admin_ids:
        raise RuntimeError("Укажите хотя бы один ADMIN_IDS в файле .env.")

    raw_db_path = Path(os.getenv("DB_PATH", "data/support.db").strip() or "data/support.db")
    db_path = raw_db_path if raw_db_path.is_absolute() else BASE_DIR / raw_db_path

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        support_name=os.getenv("SUPPORT_NAME", "VazaVPN").strip() or "VazaVPN",
        db_path=db_path,
        archive_after_hours=max(1, _parse_int("ARCHIVE_AFTER_HOURS", 48)),
        broadcast_delay=max(0.0, _parse_float("BROADCAST_DELAY", 0.05)),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
