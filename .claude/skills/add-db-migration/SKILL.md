---
name: add-db-migration
description: Create a new PostgreSQL migration in storage/migrations/. Covers naming, conventions, and all gotchas.
---

# Add a Database Migration

Migrations are forward-only SQL files in `storage/migrations/`. They run in filename order inside a transaction.

## Step 1: Determine the next migration number

Check existing migrations:

```bash
ls storage/migrations/*.sql
```

Current migrations: 001 through 006. The next migration is `007_<name>.sql`.

## Step 2: Create the migration file

Create `storage/migrations/007_<descriptive_name>.sql`:

```sql
-- Short description of what this migration does

CREATE TABLE IF NOT EXISTS example_data (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    data JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_example_discord ON example_data(discord_id);
CREATE INDEX IF NOT EXISTS idx_example_symbol ON example_data(symbol);
CREATE INDEX IF NOT EXISTS idx_example_tags ON example_data USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_example_data ON example_data USING GIN(data);
```

## Conventions

### Always use
- `IF NOT EXISTS` on all `CREATE TABLE` and `CREATE INDEX` statements
- `TIMESTAMPTZ` (not `TIMESTAMP`) with `DEFAULT NOW()`
- `BIGINT` for Discord IDs (they exceed 32-bit range)
- `SERIAL` for auto-increment primary keys
- `TEXT[]` for array columns, `JSONB` for JSON columns
- `GIN` indexes on `TEXT[]` and `JSONB` columns
- A comment at the top describing the migration

### Column types reference
| Type | Use for |
|------|---------|
| `BIGINT` | Discord IDs, large integers |
| `SERIAL` | Auto-increment PKs |
| `VARCHAR(N)` | Short constrained strings (symbols, types) |
| `TEXT` | Long text (notes, content) |
| `TEXT[]` | Arrays of strings (symbols, tags) |
| `JSONB` | Structured data, flexible schemas |
| `BOOLEAN` | Flags with `DEFAULT TRUE/FALSE` |
| `NUMERIC(12,2)` | Money / prices |
| `TIMESTAMPTZ` | All timestamps |
| `INTEGER` | Counts, small numbers |

### CHECK constraints
Use for enum-like columns:

```sql
insight_type VARCHAR(50) NOT NULL CHECK (insight_type IN (
    'price_movement', 'earnings_upcoming', 'news_relevant'
)),
```

### ALTER TABLE (adding columns to existing tables)
```sql
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_summary BOOLEAN DEFAULT FALSE;
```

## Running

```bash
python3 -m storage.migrate
```

Migrations run inside a transaction — if any statement fails, the entire migration rolls back. A `schema_migrations` table tracks which migrations have been applied.

## Gotchas

- **Forward-only**: there is no rollback/undo mechanism. If you need to undo, create a new migration.
- **No `DROP` in production migrations**: prefer `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` over dropping and recreating.
- **Transactions are automatic**: do NOT add `BEGIN`/`COMMIT` — the migration runner wraps each file in a transaction.
- **Keep migrations small**: one logical change per file. Don't combine unrelated schema changes.
- **Default values**: always provide defaults for new columns added to existing tables (otherwise existing rows fail).
- **Index naming**: use `idx_<table>_<column>` convention.
- **Test locally**: run `python3 -m storage.migrate` before committing.

## After creating the migration

If you added a new table, you likely need a repository in `storage/repositories/`:

```python
"""Repository for example_data table."""

import asyncpg
from typing import Any


class ExampleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get(self, discord_id: int) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            "SELECT * FROM example_data WHERE discord_id = $1 ORDER BY created_at DESC",
            discord_id,
        )
        return [dict(r) for r in rows]

    async def upsert(self, discord_id: int, symbol: str, **kwargs: Any) -> int:
        return await self.pool.fetchval(
            """INSERT INTO example_data (discord_id, symbol, data)
               VALUES ($1, $2, $3)
               ON CONFLICT (discord_id, symbol) DO UPDATE
               SET data = $3, updated_at = NOW()
               RETURNING id""",
            discord_id, symbol, kwargs.get("data", {}),
        )
```

## Checklist

- [ ] Next sequential number (check existing files)
- [ ] `IF NOT EXISTS` on all CREATE statements
- [ ] `TIMESTAMPTZ DEFAULT NOW()` for timestamps
- [ ] `BIGINT` for Discord IDs
- [ ] Appropriate indexes created
- [ ] Comment at top describing the migration
- [ ] Tested with `python3 -m storage.migrate`
