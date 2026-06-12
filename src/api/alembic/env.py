import os
import psycopg
from logging.config import fileConfig

from alembic import context

config = context.config

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
    # Use psycopg v3 directly — the app does not use SQLAlchemy, so psycopg2
    # is not installed. RCARS_DATABASE_URL uses plain postgresql:// which
    # psycopg.connect() accepts natively.
    url = config.get_main_option("sqlalchemy.url")
    with psycopg.connect(url) as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
