import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context  # type: ignore[attr-defined]

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Default DB file when DATABASE_PATH is not set. Must mirror the application's
# default (config/settings.py, adapters/api/dependencies.py, scripts/create_demo_users.py).
DEFAULT_DB_FILE = "colony_manager.sqlite"


def _database_url() -> str:
    """Resolve the SQLite URL the same way the running app does.

    ``DATABASE_PATH`` (set by docker-compose to ``/data/colony_manager.sqlite``
    and by ``.env.production``) wins when present; otherwise fall back to the
    default ``colony_manager.sqlite`` in the project root (the parent of this
    ``alembic/`` directory). Keeping Alembic on the app's exact resolution
    prevents migrations targeting a different file than the one the backend
    reads (the drift that previously pointed at a stale ``data/`` copy).
    """
    if configured := os.getenv("DATABASE_PATH"):
        return f"sqlite:///{Path(configured).expanduser().resolve().as_posix()}"
    project_root = Path(__file__).resolve().parent.parent
    return f"sqlite:///{(project_root / DEFAULT_DB_FILE).as_posix()}"

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from colony_manager.adapters.persistence.orm_models import Base  # noqa: E402

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    config_section = dict(config.get_section(config.config_ini_section, {}))
    config_section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
