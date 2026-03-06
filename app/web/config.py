import typing
import yaml

if typing.TYPE_CHECKING:
    from .app import Application

def setup_config(app: "Application", config_path: str) -> None:
    with open(config_path, "r") as f:
        app.config = yaml.safe_load(f)