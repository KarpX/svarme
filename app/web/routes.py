from aiohttp.web_app import Application

__all__ = ("setup_routes",)


def setup_routes(application: Application):
    import app.users.routes
    import app.admin.routes

    app.users.routes.register_urls(application)
    app.admin.routes.register_urls(application)