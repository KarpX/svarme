import typing
from dataclasses import dataclass
import yaml


@dataclass
class BotConfig:
    token: str

@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass
class AdminConfig:
    email: str
    password: str

@dataclass
class RedisConfig:
    host: str
    port: int
    password: str
    db: int

@dataclass
class Config:
    bot: BotConfig
    database: DatabaseConfig
    admin: AdminConfig
    gigachat: BotConfig
    redis: RedisConfig

if typing.TYPE_CHECKING:
    from .app import Application

def setup_config(app: "Application", config_path: str) -> None:
    with open(config_path, "r") as f:
        app.config = yaml.safe_load(f)

    app.config = Config(
        bot=BotConfig(token=app.config["bot"]["token"]),
        database=DatabaseConfig(**app.config["database"]),
        admin=AdminConfig(**app.config["admin"]),
        gigachat=BotConfig(token=app.config["gigachat"]["token"]),
        redis=RedisConfig(**app.config["redis"])
    )
