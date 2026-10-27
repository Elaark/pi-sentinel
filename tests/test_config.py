import pytest

from pi_sentinel.config import Config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("DISCORD_TOKEN", "WEBHOOK_URL", "TEMP_WARNING"):
        monkeypatch.delenv(key, raising=False)


def test_loads_values_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# comment\nDISCORD_TOKEN=abc\nWEBHOOK_URL="https://discord.com/api/webhooks/1/x"\nTEMP_WARNING=70\n'
    )
    config = Config.from_env(env_file)
    assert config.discord_token == "abc"
    assert config.webhook_url == "https://discord.com/api/webhooks/1/x"
    assert config.temp_warning == 70.0
    assert config.temp_critical == 82.0


def test_environment_takes_precedence_over_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DISCORD_TOKEN=from_file\nWEBHOOK_URL=https://x\n")
    monkeypatch.setenv("DISCORD_TOKEN", "from_env")
    assert Config.from_env(env_file).discord_token == "from_env"


def test_missing_variables_stop_the_program(tmp_path):
    with pytest.raises(SystemExit, match="DISCORD_TOKEN"):
        Config.from_env(tmp_path / "does-not-exist")
