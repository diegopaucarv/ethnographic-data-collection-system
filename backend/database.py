"""Database connection and pooling for Ayni collection system."""
import asyncio
import os
import asyncpg
from typing import Optional

pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create a pool bound to the active event loop."""
    global pool
    active_loop = asyncio.get_running_loop()
    pool_loop = getattr(pool, "_loop", None) if pool is not None else None
    pool_is_closed = bool(getattr(pool, "_closed", False)) if pool is not None else False

    if pool is not None and (pool_is_closed or pool_loop is not active_loop):
        # asyncpg pools are event-loop bound; do not await close() on a pool
        # owned by a loop that pytest or a worker has already stopped.
        if pool_loop is active_loop and not pool_is_closed:
            await pool.close()
        pool = None

    if pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=int(os.environ.get("DB_POOL_MIN_SIZE", "1")),
            max_size=int(os.environ.get("DB_POOL_MAX_SIZE", "5")),
            command_timeout=60,
        )
    return pool


async def close_pool():
    """Close the connection pool."""
    global pool
    if pool is not None:
        await pool.close()
        pool = None


async def execute(query: str, *args):
    """Execute a query that returns no results."""
    p = await get_pool()
    return await p.execute(query, *args)


async def fetch(query: str, *args) -> list[dict]:
    """Fetch multiple rows as dictionaries."""
    p = await get_pool()
    rows = await p.fetch(query, *args)
    return [dict(r) for r in rows]


async def fetchrow(query: str, *args) -> Optional[dict]:
    """Fetch a single row as a dictionary."""
    p = await get_pool()
    row = await p.fetchrow(query, *args)
    return dict(row) if row else None


async def fetchval(query: str, *args):
    """Fetch a single value."""
    p = await get_pool()
    return await p.fetchval(query, *args)
