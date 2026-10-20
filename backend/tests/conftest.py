import os
from collections.abc import Generator

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Test isolation must be established before importing the application, whose
# module-level engine reads settings immediately. Environment variables take
# precedence over any developer backend/.env that may point at shared Supabase.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:////tmp/aso_compass_pytest_bootstrap.db"
os.environ["RUN_WORKER_ENABLED"] = "false"
os.environ["AI_ENABLED"] = "false"
os.environ["AI_ACCESS_TOKEN_HASH"] = "11caa243f14b435cf3723169bb9efe0efb58acf790349ac6780f028b98a7572c"
os.environ.pop("OPENAI_API_KEY", None)

from app.core.settings import Settings, get_settings
from app.db.session import get_session
from app.main import app


@pytest.fixture
def api(tmp_path) -> Generator[tuple[object, object], None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    settings = Settings(
        app_env="test", database_url=f"sqlite:///{tmp_path / 'test.db'}", run_worker_enabled=False
    )

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    yield app, engine
    app.dependency_overrides.clear()
