from aiohttp import web
from aiohttp.web import Application as AiohttpApplication

from app.store.store import setup_store
from app.web.config import setup_config
from app.web.logger import setup_logging
from app.web.mw import auth_middleware
from app.web.routes import setup_routes

__all__ = ("Application",)


class Application(AiohttpApplication):
    config = None
    store = None
    database = None


def setup_app(config_path: str) -> Application:
    app = Application(middlewares=[auth_middleware])
    app["admin_sessions"] = set()

    setup_logging(app)
    setup_config(app, config_path)
    setup_routes(app)
    setup_store(app)

    return app


if __name__ == "__main__":
    app = setup_app("./config.yaml")
    web.run_app(app, port=8000)
