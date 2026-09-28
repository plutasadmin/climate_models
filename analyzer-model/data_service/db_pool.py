"""Shared PostgreSQL connection pools for analyzer-model data access."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager, contextmanager
from threading import Lock
from typing import Any, AsyncIterator, Dict, Iterator, Optional

import asyncpg
import psycopg2
from psycopg2 import pool as psycopg2_pool

logger = logging.getLogger(__name__)

_PSYCOPG2_MAX_RETRIES = 5
_ASYNCPG_MAX_RETRIES = 5

_psycopg2_pools: Dict[str, psycopg2_pool.ThreadedConnectionPool] = {}
_asyncpg_pools: Dict[str, asyncpg.Pool] = {}
_psycopg2_lock = Lock()
_asyncpg_lock = asyncio.Lock()


def _pool_key(config: Dict[str, Any]) -> str:
    return (
        f"{config.get('host')}:{config.get('port')}:"
        f"{config.get('database')}:{config.get('user')}"
    )


def _is_recovery_mode_error(exc: BaseException) -> bool:
    return "database system is in recovery mode" in str(exc).lower()


def _is_stale_connection_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    stale_markers = (
        "server closed the connection unexpectedly",
        "connection not open",
        "connection is closed",
        "terminating connection",
        "connection reset",
        "broken pipe",
        "could not connect to server",
        "connection timed out",
        "database system is in recovery mode",
    )
    if any(marker in message for marker in stale_markers):
        return True
    return isinstance(exc, (psycopg2.InterfaceError, psycopg2.OperationalError, asyncpg.InterfaceError))


def get_psycopg2_pool(config: Dict[str, Any], minconn: int = 1, maxconn: int = 20):
    """Return a process-wide psycopg2 pool for the given database config."""
    key = _pool_key(config)
    with _psycopg2_lock:
        if key not in _psycopg2_pools:
            _psycopg2_pools[key] = psycopg2_pool.ThreadedConnectionPool(
                minconn,
                maxconn,
                database=config["database"],
                user=config["user"],
                password=config["password"],
                host=config["host"],
                port=config["port"],
            )
        return _psycopg2_pools[key]


def reset_psycopg2_pool(config: Dict[str, Any], minconn: int = 1, maxconn: int = 20):
    """Drop and recreate a psycopg2 pool (used after recovery-mode / failover)."""
    key = _pool_key(config)
    with _psycopg2_lock:
        old = _psycopg2_pools.pop(key, None)
        if old is not None:
            try:
                old.closeall()
            except Exception:
                pass
        _psycopg2_pools[key] = psycopg2_pool.ThreadedConnectionPool(
            minconn,
            maxconn,
            database=config["database"],
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
        )
        return _psycopg2_pools[key]


def release_psycopg2_connection(
    pool: psycopg2_pool.ThreadedConnectionPool,
    conn,
    *,
    discard: bool = False,
) -> None:
    """Return a psycopg2 connection to the pool, discarding broken sockets when needed."""
    if conn is None:
        return
    try:
        pool.putconn(conn, close=discard)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def borrow_psycopg2_connection(
    pool: psycopg2_pool.ThreadedConnectionPool,
    *,
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = _PSYCOPG2_MAX_RETRIES,
) -> Iterator[Any]:
    """Borrow a live psycopg2 connection, retrying when the pool hands out stale sockets."""
    last_error: Optional[BaseException] = None
    active_pool = pool

    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = active_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            try:
                yield conn
            finally:
                exc = sys.exc_info()[1]
                discard = exc is not None and _is_stale_connection_error(exc)
                release_psycopg2_connection(active_pool, conn, discard=discard)
            return
        except Exception as exc:
            last_error = exc
            discard = _is_stale_connection_error(exc)
            release_psycopg2_connection(active_pool, conn, discard=discard)
            if discard and attempt < max_retries:
                logger.warning(
                    "Discarding stale psycopg2 connection (attempt %s/%s): %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if _is_recovery_mode_error(exc) and config is not None:
                    active_pool = reset_psycopg2_pool(config)
                    # Recovery usually needs a few seconds; backoff before retrying.
                    time.sleep(min(2 ** (attempt - 1), 8))
                elif discard:
                    time.sleep(0.5 * attempt)
                continue
            raise

    if last_error is not None:
        raise last_error


async def get_asyncpg_pool(config: Dict[str, Any], min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    """Return a process-wide asyncpg pool for the given database config."""
    key = _pool_key(config)
    async with _asyncpg_lock:
        pool = _asyncpg_pools.get(key)
        if pool is None:
            pool = await asyncpg.create_pool(
                database=config["database"],
                user=config["user"],
                password=config["password"],
                host=config["host"],
                port=config["port"],
                min_size=min_size,
                max_size=max_size,
                max_inactive_connection_lifetime=120,
                command_timeout=120,
            )
            _asyncpg_pools[key] = pool
        return pool


async def reset_asyncpg_pool(config: Dict[str, Any], min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    """Drop and recreate an asyncpg pool after recovery-mode / failover."""
    key = _pool_key(config)
    async with _asyncpg_lock:
        old = _asyncpg_pools.pop(key, None)
        if old is not None:
            try:
                await old.close()
            except Exception:
                pass
        pool = await asyncpg.create_pool(
            database=config["database"],
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            min_size=min_size,
            max_size=max_size,
            max_inactive_connection_lifetime=120,
            command_timeout=120,
        )
        _asyncpg_pools[key] = pool
        return pool


@asynccontextmanager
async def borrow_asyncpg_connection(
    config: Dict[str, Any],
    *,
    max_retries: int = _ASYNCPG_MAX_RETRIES,
) -> AsyncIterator[asyncpg.Connection]:
    """Borrow a live asyncpg connection with stale-connection retry."""
    pool = await get_asyncpg_pool(config)
    last_error: Optional[BaseException] = None

    for attempt in range(1, max_retries + 1):
        conn = await pool.acquire()
        try:
            await conn.execute("SELECT 1")
            try:
                yield conn
            finally:
                exc = sys.exc_info()[1]
                if conn.is_in_transaction():
                    await conn.execute("ROLLBACK")
                await pool.release(conn, timeout=1)
            return
        except Exception as exc:
            last_error = exc
            try:
                if conn.is_in_transaction():
                    await conn.execute("ROLLBACK")
            except Exception:
                pass
            try:
                await pool.release(conn, timeout=1)
            except Exception:
                pass
            if _is_stale_connection_error(exc) and attempt < max_retries:
                logger.warning(
                    "Discarding stale asyncpg connection (attempt %s/%s): %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if _is_recovery_mode_error(exc):
                    pool = await reset_asyncpg_pool(config)
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                else:
                    await asyncio.sleep(0.5 * attempt)
                continue
            raise

    if last_error is not None:
        raise last_error


async def close_all_pools() -> None:
    """Close all pools (useful for tests/shutdown)."""
    with _psycopg2_lock:
        for pool in _psycopg2_pools.values():
            pool.closeall()
        _psycopg2_pools.clear()

    async with _asyncpg_lock:
        for pool in _asyncpg_pools.values():
            await pool.close()
        _asyncpg_pools.clear()
