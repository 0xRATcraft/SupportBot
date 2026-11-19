from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot import texts
from bot.client import SupportBot
from bot.config import Config, load_config
from bot.db import Database
from bot.handlers import admin, common, user
from bot.middlewares import AccessMiddleware, AdminOnlyMiddleware
from bot.scheduler import archive_stale_loop

logger = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    config: Config = load_config()
    setup_logging(config.log_level)

    db = Database(config.db_path)
    await db.connect()

    bot = SupportBot(
        token=config.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN_V2,
            link_preview_is_disabled=True,
        ),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["config"] = config

    access = AccessMiddleware(db, config.admin_ids)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)

    # Админский роутер пропускает только администраторов. Фильтр на уровне
    # роутера не мешает обычным пользователям попадать в user.router.
    admin.router.message.filter(F.from_user.id.in_(config.admin_ids))
    admin.router.callback_query.filter(F.from_user.id.in_(config.admin_ids))

    admin_only = AdminOnlyMiddleware(config.admin_ids)
    admin.router.message.middleware(admin_only)
    admin.router.callback_query.middleware(admin_only)

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    scheduler_task = asyncio.create_task(
        archive_stale_loop(bot, db, config),
        name="archive-stale-tickets",
    )

    @dp.errors()
    async def error_handler(event: ErrorEvent) -> bool:
        logger.exception("Необработанная ошибка", exc_info=event.exception)
        update = event.update
        try:
            if update.callback_query is not None:
                await update.callback_query.answer(
                    "Произошла ошибка. Попробуйте ещё раз.",
                    show_alert=True,
                )
            elif update.message is not None:
                await update.message.answer(texts.error_message())
        except Exception:
            pass
        return True

    log = logging.getLogger(__name__)
    log.info("Бот запущен. Администраторы: %s", sorted(config.admin_ids))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger(__name__).exception("Не удалось запустить бота: %s", exc)
        raise
