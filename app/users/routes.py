from aiohttp.web_app import Application

__all__ = ("register_urls",)


def register_urls(application: Application):
    from app.users.views import AdminLoginView, AdminLogoutView

    application.router.add_view("/admin/login", AdminLoginView)
    application.router.add_view("/admin/logout", AdminLogoutView)