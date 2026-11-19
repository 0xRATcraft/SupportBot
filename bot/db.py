from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import aiosqlite

from .content import Content

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT NOT NULL,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_names (
    telegram_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    admin_unread INTEGER NOT NULL DEFAULT 1,
    close_requested INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_user_message_at TEXT,
    last_admin_message_at TEXT,
    archived_at TEXT,
    closed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tickets_user_status
    ON tickets(user_id, status, is_deleted);
CREATE INDEX IF NOT EXISTS idx_tickets_admin_list
    ON tickets(is_deleted, status, admin_unread, last_user_message_at);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    sender_type TEXT NOT NULL,
    sender_name TEXT,
    text TEXT,
    file_id TEXT,
    file_type TEXT,
    file_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_ticket
    ON messages(ticket_id, id);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def connect(self) -> None:
        if not str(self.path).startswith(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _fetchone_locked(
        self, sql: str, params: Iterable[Any] = ()
    ) -> dict[str, Any] | None:
        cursor = await self.conn.execute(sql, tuple(params))
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row is not None else None

    async def _fetchall_locked(
        self, sql: str, params: Iterable[Any] = ()
    ) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(sql, tuple(params))
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]

    async def _fetchone(
        self, sql: str, params: Iterable[Any] = ()
    ) -> dict[str, Any] | None:
        async with self._lock:
            return await self._fetchone_locked(sql, params)

    async def _fetchall(
        self, sql: str, params: Iterable[Any] = ()
    ) -> list[dict[str, Any]]:
        async with self._lock:
            return await self._fetchall_locked(sql, params)

    # ------------------------------------------------------------------ users

    async def upsert_user(
        self, user_id: int, username: str | None, full_name: str
    ) -> None:
        now = utcnow()
        async with self._lock:
            await self.conn.execute(
                """
                INSERT INTO users (telegram_id, username, full_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, full_name, now, now),
            )
            await self.conn.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            "SELECT * FROM users WHERE telegram_id = ?", (user_id,)
        )

    async def find_user(self, query: str) -> dict[str, Any] | None:
        query = query.strip()
        if query.startswith("@"):
            query = query[1:]
        if not query:
            return None
        if query.isdigit():
            user = await self.get_user(int(query))
            if user is not None:
                return user
        return await self._fetchone(
            "SELECT * FROM users WHERE lower(username) = lower(?) LIMIT 1", (query,)
        )

    async def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        async with self._lock:
            await self.conn.execute(
                "UPDATE users SET is_blocked = ?, updated_at = ? WHERE telegram_id = ?",
                (1 if blocked else 0, utcnow(), user_id),
            )
            await self.conn.commit()

    async def set_operator_name(self, user_id: int, name: str) -> None:
        async with self._lock:
            await self.conn.execute(
                """
                INSERT INTO operator_names (telegram_id, name, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = excluded.updated_at
                """,
                (user_id, name, utcnow()),
            )
            await self.conn.commit()

    async def get_operator_name(self, user_id: int) -> str | None:
        row = await self._fetchone(
            "SELECT name FROM operator_names WHERE telegram_id = ?",
            (user_id,),
        )
        return str(row["name"]) if row else None

    async def clear_operator_name(self, user_id: int) -> None:
        async with self._lock:
            await self.conn.execute(
                "DELETE FROM operator_names WHERE telegram_id = ?",
                (user_id,),
            )
            await self.conn.commit()

    async def count_user_tickets(self, user_id: int) -> int:
        row = await self._fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM tickets
            WHERE user_id = ? AND is_deleted = 0
            """,
            (user_id,),
        )
        return int(row["cnt"]) if row else 0

    # ---------------------------------------------------------------- tickets

    async def create_ticket_with_message(
        self,
        user_id: int,
        sender_name: str,
        content: Content,
    ) -> int:
        now = utcnow()
        async with self._lock:
            cursor = await self.conn.execute(
                """
                INSERT INTO tickets (
                    user_id, status, admin_unread, created_at, updated_at,
                    last_user_message_at
                )
                VALUES (?, 'open', 1, ?, ?, ?)
                """,
                (user_id, now, now, now),
            )
            ticket_id = int(cursor.lastrowid)
            await cursor.close()
            await self.conn.execute(
                """
                INSERT INTO messages (
                    ticket_id, sender_id, sender_type, sender_name,
                    text, file_id, file_type, file_name, created_at
                )
                VALUES (?, ?, 'user', ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    user_id,
                    sender_name,
                    content.text,
                    content.file_id,
                    content.file_type,
                    content.file_name,
                    now,
                ),
            )
            await self.conn.commit()
        return ticket_id

    async def get_active_ticket(self, user_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT t.*, u.username, u.full_name
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.user_id = ?
              AND t.is_deleted = 0
              AND t.status IN ('open', 'answered')
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (user_id,),
        )

    async def get_ticket(self, ticket_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT t.*, u.username, u.full_name,
                   (SELECT COUNT(*) FROM messages m WHERE m.ticket_id = t.id) AS message_count
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.id = ? AND t.is_deleted = 0
            """,
            (ticket_id,),
        )

    async def get_ticket_for_user(
        self, ticket_id: int, user_id: int
    ) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT t.*, u.username, u.full_name,
                   (SELECT COUNT(*) FROM messages m WHERE m.ticket_id = t.id) AS message_count
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.id = ? AND t.user_id = ? AND t.is_deleted = 0
            """,
            (ticket_id, user_id),
        )

    async def add_message(
        self,
        ticket_id: int,
        sender_id: int,
        sender_type: str,
        sender_name: str,
        content: Content,
    ) -> dict[str, Any] | None:
        now = utcnow()
        async with self._lock:
            ticket = await self._fetchone_locked(
                "SELECT * FROM tickets WHERE id = ? AND is_deleted = 0",
                (ticket_id,),
            )
            if ticket is None:
                return None

            status = str(ticket["status"])
            if status == "closed":
                return None

            cursor = await self.conn.execute(
                """
                INSERT INTO messages (
                    ticket_id, sender_id, sender_type, sender_name,
                    text, file_id, file_type, file_name, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    sender_id,
                    sender_type,
                    sender_name,
                    content.text,
                    content.file_id,
                    content.file_type,
                    content.file_name,
                    now,
                ),
            )
            message_id = int(cursor.lastrowid)
            await cursor.close()

            if sender_type == "user":
                new_status = "open"
                await self.conn.execute(
                    """
                    UPDATE tickets
                    SET status = ?, admin_unread = 1, close_requested = 0,
                        last_user_message_at = ?, updated_at = ?, archived_at = NULL
                    WHERE id = ?
                    """,
                    (new_status, now, now, ticket_id),
                )
            else:
                new_status = "answered"
                await self.conn.execute(
                    """
                    UPDATE tickets
                    SET status = ?, admin_unread = 0, close_requested = 0,
                        last_admin_message_at = ?, updated_at = ?, archived_at = NULL
                    WHERE id = ?
                    """,
                    (new_status, now, now, ticket_id),
                )

            await self.conn.commit()

        return {
            "message_id": message_id,
            "previous_status": status,
            "new_status": new_status,
            "ticket_user_id": int(ticket["user_id"]),
        }

    async def mark_admin_read(self, ticket_id: int) -> None:
        async with self._lock:
            await self.conn.execute(
                "UPDATE tickets SET admin_unread = 0 WHERE id = ?",
                (ticket_id,),
            )
            await self.conn.commit()

    async def close_ticket(self, ticket_id: int) -> bool:
        now = utcnow()
        async with self._lock:
            cursor = await self.conn.execute(
                """
                UPDATE tickets
                SET status = 'closed', closed_at = ?, updated_at = ?,
                    admin_unread = 0, close_requested = 0
                WHERE id = ? AND is_deleted = 0 AND status != 'closed'
                """,
                (now, now, ticket_id),
            )
            await self.conn.commit()
            changed = cursor.rowcount > 0
            await cursor.close()
        return changed

    async def archive_ticket(self, ticket_id: int) -> bool:
        now = utcnow()
        async with self._lock:
            cursor = await self.conn.execute(
                """
                UPDATE tickets
                SET status = 'archived', archived_at = ?, updated_at = ?,
                    admin_unread = 0, close_requested = 0
                WHERE id = ? AND is_deleted = 0 AND status = 'answered'
                """,
                (now, now, ticket_id),
            )
            await self.conn.commit()
            changed = cursor.rowcount > 0
            await cursor.close()
        return changed

    async def set_close_requested(self, ticket_id: int, requested: bool) -> None:
        now = utcnow()
        async with self._lock:
            if requested:
                # Предложение закрытия сбрасывает 48-часовой таймер архивации.
                await self.conn.execute(
                    """
                    UPDATE tickets
                    SET close_requested = 1, updated_at = ?, last_admin_message_at = ?
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (now, now, ticket_id),
                )
            else:
                await self.conn.execute(
                    """
                    UPDATE tickets
                    SET close_requested = 0, updated_at = ?
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (now, ticket_id),
                )
            await self.conn.commit()

    async def soft_delete_ticket(self, ticket_id: int) -> dict[str, Any] | None:
        now = utcnow()
        async with self._lock:
            ticket = await self._fetchone_locked(
                "SELECT * FROM tickets WHERE id = ? AND is_deleted = 0",
                (ticket_id,),
            )
            if ticket is None:
                return None
            await self.conn.execute(
                """
                UPDATE tickets
                SET is_deleted = 1, updated_at = ?, admin_unread = 0,
                    close_requested = 0
                WHERE id = ?
                """,
                (now, ticket_id),
            )
            await self.conn.commit()
        return ticket

    # -------------------------------------------------------------- listings

    async def get_admin_tickets(
        self, mode: str, page: int, page_size: int = 8
    ) -> tuple[list[dict[str, Any]], int, int]:
        page = max(0, page)
        statuses = ("archived", "closed") if mode == "archive" else ("open", "answered")
        placeholders = ", ".join("?" for _ in statuses)
        count_row = await self._fetchone(
            f"""
            SELECT COUNT(*) AS cnt
            FROM tickets
            WHERE is_deleted = 0 AND status IN ({placeholders})
            """,
            statuses,
        )
        total = int(count_row["cnt"]) if count_row else 0
        pages = max(1, math.ceil(total / page_size))

        if mode == "archive":
            order_by = "t.updated_at DESC, t.id DESC"
        else:
            # 1) старые обращения с новым ответом пользователя;
            # 2) более новые обращения с ответом оператора;
            # 3) остальные.
            order_by = """
                CASE
                    WHEN t.admin_unread = 1 THEN 0
                    WHEN t.status = 'answered' THEN 1
                    ELSE 2
                END ASC,
                CASE WHEN t.admin_unread = 1 THEN t.last_user_message_at END ASC,
                CASE WHEN t.admin_unread = 0 THEN t.updated_at END DESC,
                t.id DESC
            """

        rows = await self._fetchall(
            f"""
            SELECT t.*, u.username, u.full_name,
                   (SELECT m.text FROM messages m
                    WHERE m.ticket_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_text,
                   (SELECT m.file_type FROM messages m
                    WHERE m.ticket_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_file_type
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.is_deleted = 0 AND t.status IN ({placeholders})
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*statuses, page_size, page * page_size),
        )
        return rows, total, pages

    async def get_user_archive(
        self, user_id: int, page: int, page_size: int = 8
    ) -> tuple[list[dict[str, Any]], int, int]:
        page = max(0, page)
        count_row = await self._fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM tickets
            WHERE user_id = ? AND is_deleted = 0
              AND status IN ('archived', 'closed')
            """,
            (user_id,),
        )
        total = int(count_row["cnt"]) if count_row else 0
        pages = max(1, math.ceil(total / page_size))
        rows = await self._fetchall(
            """
            SELECT t.*, u.username, u.full_name
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.user_id = ? AND t.is_deleted = 0
              AND t.status IN ('archived', 'closed')
            ORDER BY t.updated_at DESC, t.id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, page * page_size),
        )
        return rows, total, pages

    async def get_messages(
        self, ticket_id: int, limit: int = 50
    ) -> tuple[list[dict[str, Any]], int]:
        async with self._lock:
            count_row = await self._fetchone_locked(
                "SELECT COUNT(*) AS cnt FROM messages WHERE ticket_id = ?",
                (ticket_id,),
            )
            total = int(count_row["cnt"]) if count_row else 0
            rows = await self._fetchall_locked(
                """
                SELECT * FROM (
                    SELECT * FROM messages
                    WHERE ticket_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (ticket_id, limit),
            )
        return rows, total

    async def get_stale_answered(self, cutoff: str) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT t.*, u.username, u.full_name
            FROM tickets t
            JOIN users u ON u.telegram_id = t.user_id
            WHERE t.is_deleted = 0
              AND t.status = 'answered'
              AND t.last_admin_message_at IS NOT NULL
              AND t.last_admin_message_at <= ?
            ORDER BY t.last_admin_message_at ASC
            """,
            (cutoff,),
        )

    async def get_broadcast_user_ids(self) -> list[int]:
        rows = await self._fetchall(
            "SELECT telegram_id FROM users WHERE is_blocked = 0 ORDER BY telegram_id"
        )
        return [int(row["telegram_id"]) for row in rows]

    async def get_stats(self) -> dict[str, int]:
        async with self._lock:
            users = await self._fetchone_locked(
                "SELECT COUNT(*) AS cnt FROM users"
            )
            blocked = await self._fetchone_locked(
                "SELECT COUNT(*) AS cnt FROM users WHERE is_blocked = 1"
            )
            active = await self._fetchone_locked(
                """
                SELECT COUNT(*) AS cnt FROM tickets
                WHERE is_deleted = 0 AND status IN ('open', 'answered')
                """
            )
            archive = await self._fetchone_locked(
                """
                SELECT COUNT(*) AS cnt FROM tickets
                WHERE is_deleted = 0 AND status IN ('archived', 'closed')
                """
            )
        return {
            "users_total": int(users["cnt"]) if users else 0,
            "users_blocked": int(blocked["cnt"]) if blocked else 0,
            "active_tickets": int(active["cnt"]) if active else 0,
            "archive_tickets": int(archive["cnt"]) if archive else 0,
        }
