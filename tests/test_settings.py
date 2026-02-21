from bt_service.settings import Settings


def test_resolved_log_defaults_by_env() -> None:
    dev = Settings(app_env="dev", log_level="AUTO")
    staging = Settings(app_env="staging", log_level="AUTO")
    prod = Settings(app_env="prod", log_level="AUTO")

    assert dev.resolved_log_level == "DEBUG"
    assert staging.resolved_log_level == "INFO"
    assert prod.resolved_log_level == "WARNING"
    assert dev.resolved_log_json is False
    assert staging.resolved_log_json is True
    assert prod.resolved_log_json is True


def test_resolved_api_reload_for_prod() -> None:
    dev = Settings(app_env="dev", api_reload=True)
    prod = Settings(app_env="prod", api_reload=True)

    assert dev.resolved_api_reload is True
    assert prod.resolved_api_reload is False


def test_jira_env_specific_overrides() -> None:
    settings = Settings(
        app_env="staging",
        jira_base_url="https://fallback.example.com",
        jira_base_url_staging="https://staging.example.com",
        jira_user_email="fallback@example.com",
        jira_user_email_staging="staging@example.com",
        jira_api_token="fallback-token",
        jira_api_token_staging="staging-token",
    )

    assert settings.resolved_jira_base_url == "https://staging.example.com"
    assert settings.resolved_jira_user_email == "staging@example.com"
    assert settings.resolved_jira_api_token == "staging-token"
