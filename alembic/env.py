import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

# Override DB URL from environment if available
db_url = os.environ.get("RCARS_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # SQLAlchemy requires the psycopg v3 driver to be specified explicitly.
    # RCARS_DATABASE_URL uses plain postgresql:// (for direct psycopg.connect use);
    # swap the scheme here so SQLAlchemy routes to psycopg v3, not psycopg2.
    url = config.get_main_option("sqlalchemy.url").replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
