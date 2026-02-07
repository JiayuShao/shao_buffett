"""Async PostgreSQL connection pool manager."""

import json
import asyncpg
import structlog
from pathlib import Path
from config.settings import settings

log = structlog.get_logger(__name__)

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Set up JSON codec so JSONB columns return dicts/lists, not strings."""
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
            init=_init_connection,
        )
        log.info("database_pool_created")
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        log.info("database_pool_closed")


async def run_migrations() -> None:
    """Run all SQL migration files in order."""
    pool = await get_pool()
    migrations_dir = Path(__file__).parent / "migrations"

    async with pool.acquire() as conn:
        # Create migrations tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM _migrations")
        }

        migration_files = sorted(migrations_dir.glob("*.sql"))
        for migration_file in migration_files:
            if migration_file.name in applied:
                continue

            log.info("applying_migration", filename=migration_file.name)
            sql = migration_file.read_text()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (filename) VALUES ($1)",
                    migration_file.name,
                )
            log.info("migration_applied", filename=migration_file.name)
