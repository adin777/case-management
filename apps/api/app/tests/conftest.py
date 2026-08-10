import os
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="case-management-tests-", dir=PROJECT_ROOT / "data")
TEST_DATABASE = Path(TEST_DIRECTORY.name) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET"] = "test-only-secret"
os.environ["ATTACHMENT_DIRECTORY"] = str(Path(TEST_DIRECTORY.name) / "attachments")
os.environ["KNOWLEDGE_DIRECTORY"] = str(Path(TEST_DIRECTORY.name) / "knowledge")
os.environ["SEED_DEMO_USERS"] = "true"


def pytest_configure() -> None:
    from alembic.config import Config

    from alembic import command
    from app.seed import run

    command.upgrade(Config("alembic.ini"), "head")
    run(include_demo_data=True)


def pytest_sessionfinish() -> None:
    from app.database.session import engine

    engine.dispose()
    TEST_DIRECTORY.cleanup()
