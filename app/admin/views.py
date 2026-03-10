from aiohttp import web
from pydantic import ValidationError

from app.admin.schema import (
    CategoryCreateSchema,
    CategorySchema,
    QuestionCreateSchema,
    QuestionSchema,
)


class CategoriesView(web.View):
    async def get(self):
        categories = await self.request.app.store.quiz.list_categories()
        return web.json_response(
            [CategorySchema.model_validate(c).model_dump() for c in categories]
        )

    async def post(self):
        try:
            data = await self.request.json()
            payload = CategoryCreateSchema.model_validate(data)
        except ValidationError as e:
            return web.json_response({"error": e.errors()}, status=400)

        category = await self.request.app.store.quiz.create_category(
            name=payload.name, round=payload.round
        )
        return web.json_response(
            CategorySchema.model_validate(category).model_dump(), status=201
        )


class QuestionsView(web.View):
    async def get(self):
        category_id = self.request.rel_url.query.get("category_id")
        if category_id is not None:
            try:
                category_id = int(category_id)
            except ValueError:
                return web.json_response({"error": "Invalid category_id"}, status=400)

        questions = await self.request.app.store.quiz.list_questions(
            category_id=category_id
        )
        return web.json_response(
            [QuestionSchema.model_validate(q).model_dump() for q in questions]
        )

    async def post(self):
        try:
            data = await self.request.json()
            payload = QuestionCreateSchema.model_validate(data)
        except ValidationError as e:
            return web.json_response({"error": e.errors()}, status=400)

        category = await self.request.app.store.quiz.get_category_by_id(
            payload.category_id
        )
        if not category:
            return web.json_response({"error": "Category not found"}, status=404)

        question = await self.request.app.store.quiz.create_question(
            category_id=payload.category_id,
            text=payload.text,
            answer=payload.answer,
            price=payload.price,
        )
        return web.json_response(
            QuestionSchema.model_validate(question).model_dump(), status=201
        )
