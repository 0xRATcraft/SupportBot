from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from . import services
from .config import Config
from .db import Database

logger = logging.getLogger(__name__)


async def archive_stale_loop(bot: Bot, db: Database, config: Config) -> None:
    while True:
        try:
            cutoff = (
                datetime.now(timezone.utc)
                - timedelta(hours=config.archive_after_hours)
            ).isoformat(timespec="seconds")
            tickets = await db.get_stale_answered(cutoff)
            for ticket in tickets:
                ticket_id = int(ticket["id"])
                if await db.archive_ticket(ticket_id):
                    await services.notify_user_archived(
                        bot,
                        int(ticket["user_id"]),
                        ticket_id,
                        config.archive_after_hours,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка планировщика архивации")
        await asyncio.sleep(15 * 60)
