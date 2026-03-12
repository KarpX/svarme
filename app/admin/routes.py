from aiohttp.web_app import Application

__all__ = ("register_urls",)


def register_urls(application: Application):
    from app.admin.views import CategoriesView, QuestionsView, QuestionsImportView

    application.router.add_view("/admin/categories", CategoriesView)
    application.router.add_view("/admin/questions", QuestionsView)
    application.router.add_view("/admin/questions/import", QuestionsImportView)
