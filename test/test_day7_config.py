import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings

DATABASE = "postgresql+asyncpg://taskhub:password@localhost:5432/taskhub"
SECRET = "test-secret-key-test-secret-key-1234567890"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def configure(**values):
    return Settings(**{"DATABASE_URL": DATABASE, "SECRET_KEY": SECRET, **values})


def test_secret_is_required():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, DATABASE_URL=DATABASE)


def test_database_is_required():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, SECRET_KEY=SECRET)


@pytest.mark.parametrize(
    "key",
    [
        "tiny-key-7",
        "a" * 64,
        "secret" * 12,
        SECRET,
        "change-me-to-a-random-string-of-at-least-32-characters",
        "replace-me-with-a-generated-secret-at-least-32-characters",
    ],
)
def test_production_rejects_weak_or_sample_secret(key):
    with pytest.raises(ValidationError, match="SECRET_KEY") as error:
        configure(APP_ENV="prod", SECRET_KEY=key, REDIS_URL="redis://redis:6379/0")
    assert key not in str(error.value)


def test_production_rejects_db_echo():
    with pytest.raises(ValidationError, match="DB_ECHO must be false"):
        configure(
            APP_ENV="prod",
            SECRET_KEY=secrets.token_urlsafe(48),
            REDIS_URL="redis://redis/0",
            DB_ECHO=True,
        )


def test_production_requires_explicit_redis_url():
    with pytest.raises(
        ValidationError, match="REDIS_URL must be explicitly configured"
    ):
        configure(APP_ENV="prod", SECRET_KEY=secrets.token_urlsafe(48))


def test_production_defaults_disable_documentation():
    settings = configure(
        APP_ENV="prod",
        SECRET_KEY=secrets.token_urlsafe(48),
        REDIS_URL="rediss://redis:6380/0",
    )
    assert settings.DOCS_ENABLED is False and settings.DB_ECHO is False
    assert settings.SECRET_KEY not in repr(settings)


@pytest.mark.parametrize("env", ["dev", "test"])
def test_nonproduction_defaults_enable_documentation(env):
    settings = configure(APP_ENV=env)
    assert settings.DOCS_ENABLED is True
    assert settings.CACHE_TTL_SECONDS == 60


@pytest.mark.parametrize("env", ["staging", "../prod", "", "PROD"])
def test_invalid_environment_rejected(env):
    with pytest.raises(ValidationError, match="APP_ENV"):
        configure(APP_ENV=env)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "http://db/taskhub",
        "postgresql://user:pass@db/taskhub",
        "postgresql+asyncpg://",
        "postgresql+asyncpg://user:pass@db",
        "postgresql+asyncpg://user:pass@db:99999/taskhub",
        "sqlite+aiosqlite://",
    ],
)
def test_invalid_database_urls_rejected_in_dev(url):
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        configure(DATABASE_URL=url)


def test_sqlite_is_available_in_test_only():
    assert (
        configure(APP_ENV="test", DATABASE_URL="sqlite+aiosqlite://").DATABASE_URL
        == "sqlite+aiosqlite://"
    )
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        configure(APP_ENV="prod", DATABASE_URL="sqlite+aiosqlite://")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://redis",
        "redis://",
        "redis://redis:99999/0",
        "redis://redis/-1",
        "redis://redis/not-a-db",
        "redis://redis/0/1",
        "redis://redis/0?db=-1",
        "redis://redis/0#fragment",
        "redis://bad host/0",
    ],
)
def test_invalid_redis_urls_rejected(url):
    with pytest.raises(ValidationError, match="REDIS_URL"):
        configure(REDIS_URL=url)


@pytest.mark.parametrize(
    "url",
    [
        "redis://localhost",
        "redis://redis:6379/0",
        "rediss://user:password@redis:6380/12",
        "redis://[::1]:6379/0",
    ],
)
def test_valid_redis_urls(url):
    assert configure(REDIS_URL=url).REDIS_URL == url


@pytest.mark.parametrize("env", ["dev", "test", "prod"])
def test_environment_selects_only_its_own_file(tmp_path, monkeypatch, env):
    secret = secrets.token_urlsafe(48)
    for name in ("dev", "test", "prod"):
        (tmp_path / f".env.{name}").write_text(
            f"DATABASE_URL={DATABASE}\nSECRET_KEY={secret}\nREDIS_URL=redis://{name}:6379/0\nLOG_LEVEL=WARNING\n",
            encoding="utf-8",
        )
    monkeypatch.setenv("APP_ENV", env)
    loaded = Settings()
    assert loaded.APP_ENV == env
    assert loaded.REDIS_URL == f"redis://{env}:6379/0"
    assert loaded.LOG_LEVEL == "WARNING"


def test_dev_falls_back_to_legacy_dotenv(tmp_path):
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={DATABASE}\nSECRET_KEY={SECRET}\nLOG_LEVEL=ERROR\n",
        encoding="utf-8",
    )
    assert Settings().LOG_LEVEL == "ERROR"


def test_environment_file_does_not_inherit_missing_secret_from_dev(tmp_path):
    (tmp_path / ".env").write_text(f"SECRET_KEY={SECRET}\n", encoding="utf-8")
    (tmp_path / ".env.prod").write_text(
        f"DATABASE_URL={DATABASE}\nREDIS_URL=redis://redis/0\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(APP_ENV="prod")


def test_process_environment_overrides_file_and_init_overrides_environment(
    tmp_path, monkeypatch
):
    (tmp_path / ".env.dev").write_text(
        f"DATABASE_URL={DATABASE}\nSECRET_KEY={SECRET}\nCACHE_TTL_SECONDS=10\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CACHE_TTL_SECONDS", "20")
    assert Settings().CACHE_TTL_SECONDS == 20
    assert Settings(CACHE_TTL_SECONDS=30).CACHE_TTL_SECONDS == 30


def test_explicit_env_file_and_disabled_env_file(tmp_path):
    custom = tmp_path / "custom.env"
    custom.write_text(
        f"DATABASE_URL={DATABASE}\nSECRET_KEY={SECRET}\n", encoding="utf-8"
    )
    assert Settings(_env_file=custom).DATABASE_URL == DATABASE
    (tmp_path / ".env.dev").write_text(
        custom.read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, DATABASE_URL=DATABASE)


def test_file_cannot_change_selected_environment(tmp_path):
    (tmp_path / ".env.prod").write_text(
        f"APP_ENV=dev\nDATABASE_URL={DATABASE}\nSECRET_KEY={SECRET}\nREDIS_URL=redis://redis/0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="SECRET_KEY in prod"):
        Settings(APP_ENV="prod")


@pytest.mark.parametrize(
    "values",
    [
        {"CACHE_TTL_SECONDS": 0},
        {"ACCESS_TOKEN_EXPIRE_MINUTES": 0},
        {"REFRESH_TOKEN_EXPIRE_DAYS": -1},
        {"LOG_LEVEL": "UNKNOWN"},
        {"ALGORITHM": "none"},
    ],
)
def test_invalid_settings_fail_fast(values):
    with pytest.raises(ValidationError):
        configure(**values)
