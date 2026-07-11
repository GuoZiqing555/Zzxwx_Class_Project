"""Persistent, process-safe daily quota for upstream model requests."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_DAILY_LIMIT = 50


class QuotaExceededError(RuntimeError):
    """Raised before an upstream request when the shared daily quota is spent."""


@dataclass(frozen=True)
class QuotaStatus:
    limit: int
    used: int
    remaining: int
    day: str


def _daily_limit() -> int:
    raw_value = os.getenv("DAILY_API_CALL_LIMIT", str(DEFAULT_DAILY_LIMIT))
    try:
        limit = int(raw_value)
    except ValueError as exc:
        raise ValueError("DAILY_API_CALL_LIMIT 必须是正整数。") from exc
    if limit < 1:
        raise ValueError("DAILY_API_CALL_LIMIT 必须大于 0。")
    return limit


def _today() -> str:
    timezone_name = os.getenv("QUOTA_TIMEZONE", "Asia/Shanghai")
    try:
        return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    except Exception as exc:
        raise ValueError(f"QUOTA_TIMEZONE 无效：{timezone_name}") from exc


def _db_path() -> Path:
    return Path(os.getenv("QUOTA_DB_PATH", "data/quota.sqlite3"))


@contextmanager
def _connection() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS daily_usage (day TEXT PRIMARY KEY, used INTEGER NOT NULL)"
        )
        yield connection
    finally:
        connection.close()


def get_quota_status() -> QuotaStatus:
    """Return the shared quota status without consuming a request."""
    day = _today()
    limit = _daily_limit()
    with _connection() as connection:
        row = connection.execute(
            "SELECT used FROM daily_usage WHERE day = ?", (day,)
        ).fetchone()
    used = int(row[0]) if row else 0
    return QuotaStatus(limit=limit, used=used, remaining=max(0, limit - used), day=day)


def reserve_api_call() -> QuotaStatus:
    """Atomically reserve one billable upstream request.

    A reservation is intentionally not refunded after network/model failures: the
    provider may have received the request, so refunding could exceed the cap.
    """
    day = _today()
    limit = _daily_limit()
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT used FROM daily_usage WHERE day = ?", (day,)
        ).fetchone()
        used = int(row[0]) if row else 0
        if used >= limit:
            connection.execute("ROLLBACK")
            raise QuotaExceededError(
                f"今日体验名额已用完（全站共 {limit} 次 API 调用），请明天再试。"
            )
        used += 1
        connection.execute(
            "INSERT INTO daily_usage(day, used) VALUES(?, ?) "
            "ON CONFLICT(day) DO UPDATE SET used = excluded.used",
            (day, used),
        )
        connection.execute("COMMIT")
    return QuotaStatus(limit=limit, used=used, remaining=limit - used, day=day)
