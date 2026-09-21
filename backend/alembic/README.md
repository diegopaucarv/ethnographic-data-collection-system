# Alembic Migrations

Version control for database schema changes.

## Setup

```bash
# Install alembic
pip install alembic

# Initialize alembic in the backend directory (already done)
# alembic init alembic
```

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific revision
alembic upgrade +1
alembic upgrade 001

# Check current revision
alembic current

# See migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 001
```

## Creating New Migrations

### Automatic (not recommended for asyncpg)
```bash
alembic revision --autogenerate -m "Description of change"
```

### Manual (recommended)
```bash
alembic revision -m "Add users table"
```

Then edit the generated file in `versions/`.

## Migration Files

Located in `alembic/versions/`:

- `001_initial_schema.py` - Creates all initial tables
- Future migrations follow this pattern

Each migration file has:
- `upgrade()` - Apply the migration
- `downgrade()` - Revert the migration

## Best Practices

1. **One logical change per migration** - Easier to understand and rollback
2. **Test downgrades** - Ensure rollback works
3. **Never manually edit data** - Use ALTER/UPDATE in migrations
4. **Use descriptive names** - `002_add_image_urls_to_forms.py`
5. **Keep migrations small** - Easier to debug issues

## Troubleshooting

### Migration doesn't apply
```bash
# Check current status
alembic current

# See detailed history
alembic history --verbose
```

### Need to fix a migration
```bash
# Rollback and regenerate
alembic downgrade -1
alembic revision --autogenerate -m "Fix: ..."
alembic upgrade head
```

### Database out of sync
```bash
# Reset alembic tracking (careful!)
alembic stamp head

# Then run migrations
alembic upgrade head
```
