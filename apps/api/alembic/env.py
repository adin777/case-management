from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings
from app.database.base import Base
from app.modules import models  # noqa: F401
from app.modules.access import models as access_models  # noqa: F401
from app.modules.operations import models as operations_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    if context.dialect.name == "sqlite" and isinstance(metadata_type, __import__("sqlalchemy").Enum):
        return False
    return None


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine_from_config(
        config.get_section(config.config_ini_section) or {}, prefix="sqlalchemy.", poolclass=pool.NullPool
    ).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=compare_type)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
