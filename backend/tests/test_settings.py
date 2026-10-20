from app.core.settings import Settings


def test_frontend_origins_accept_render_friendly_comma_list(monkeypatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://localhost:5173,https://aso-compass.example")
    assert Settings().frontend_origins == ["http://localhost:5173", "https://aso-compass.example"]


def test_deployment_defaults_use_bounded_pool_and_cost_sensitive_ai_model() -> None:
    settings = Settings()
    assert settings.db_pool_size == 3
    assert settings.db_max_overflow == 2
    assert settings.db_pool_timeout_seconds == 15
    assert settings.openai_model == "gpt-6-luna"
