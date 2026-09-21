"""Database connection and pooling for Ayni collection system."""
import os
import asyncpg
from typing import Optional

pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
    global pool
    if pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=5,
            max_size=20,
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
