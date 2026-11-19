# SupportBot

Асинхронный бот технической поддержки в Telegram на **Python 3.10+ + aiogram 3 + aiosqlite**.

## Возможности

- Обращения с текстом или вложением, история переписки с оператором.
- Главное меню: новое обращение, текущее, архив, профиль.
- Закрытие обращения — по подтверждению пользователя или оператора.
- Архив с разархивированием ответом и автоархивация через `ARCHIVE_AFTER_HOURS` часов.
- Админка `/admin`: очередь обращений, пагинация, поиск пользователя, блокировка, рассылка.
- MarkdownV2 и premium-эмодзи с автоматическим откатом, если Telegram их отклонит.

## Требования

- Python 3.10+
- Токен бота от [@BotFather](https://t.me/BotFather)

## Установка

```bash
python -m venv .venv
```

Активируйте окружение:

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Установите зависимости и создайте `.env` из шаблона:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
SUPPORT_NAME=Support
DB_PATH=data/support.db
ARCHIVE_AFTER_HOURS=48
BROADCAST_DELAY=0.05
LOG_LEVEL=INFO
```

`ADMIN_IDS` можно указать несколько через запятую, например `123456789,987654321`.

## Запуск

```bash
python main.py
```

Папка `data/` и SQLite-база создаются автоматически. `.env` и содержимое `data/`
в репозиторий не попадают — коммитится только шаблон `.env.example`.

## Админка

Отправьте боту `/admin`. Доступ только у ID из `ADMIN_IDS`.

## Premium-эмодзи

В сообщениях используется MarkdownV2-разметка Telegram, например
`![📁](tg://emoji?id=6037475557082403885)`. ID эмодзи собраны в `bot/emojis.py`
(источник — `messages.md`); для кнопок используется `icon_custom_emoji_id`.

## Автор

- Поддержать автора: [pay.cloudtips.ru/p/c11527c7](https://pay.cloudtips.ru/p/c11527c7)
- Telegram-канал: [@ratcraft](https://t.me/ratcraft)

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
