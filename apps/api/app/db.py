from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine, Session

from app import models  # noqa: F401  # Import models so SQLModel metadata is registered.
from app.config import Settings
settings = Settings()
APP_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI_PATH = APP_ROOT / "alembic.ini"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# NOTE: SQLModel currently requires a sync engine for create_all and migrations.
engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


def _build_alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(APP_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)
    return config


def run_migrations() -> None:
    command.upgrade(_build_alembic_config(), "head")


def create_db_and_tables() -> None:
    run_migrations()
    from app.services.admin_auth import ensure_bootstrap_admin, log_bootstrap_result

    with session_scope() as session:
        bootstrap_result = ensure_bootstrap_admin(session)
    if bootstrap_result is not None:
        log_bootstrap_result(bootstrap_result)


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session
