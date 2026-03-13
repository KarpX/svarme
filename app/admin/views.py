import json

from aiohttp import web
from pydantic import ValidationError
from http import HTTPStatus

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
            return web.json_response({"error": e.errors()}, status=HTTPStatus.BAD_REQUEST)

        category = await self.request.app.store.quiz.create_category(
            name=payload.name, round=payload.round
        )
        return web.json_response(
            CategorySchema.model_validate(category).model_dump(), status=HTTPStatus.CREATED
        )
    
    async def patch(self):
        category_id = self.request.rel_url.query.get("category_id")
        if category_id is None:
            return web.json_response({"error": "category_id is required"}, status=HTTPStatus.BAD_REQUEST)
        
        try:
            category_id = int(category_id)
        except ValueError:
            return web.json_response({"error": "Invalid category_id"}, status=HTTPStatus.BAD_REQUEST)

        category = await self.request.app.store.quiz.get_category_by_id(category_id)
        if not category:
            return web.json_response({"error": "Category not found"}, status=HTTPStatus.NOT_FOUND)

        try:
            data = await self.request.json()
            payload = CategoryCreateSchema.model_validate(data)
        except ValidationError as e:
            return web.json_response({"error": e.errors()}, status=HTTPStatus.BAD_REQUEST)

        category.name = payload.name
        category.round = payload.round

        async with self.request.app.database.sessionmaker() as session:
            session.add(category)
            await session.commit()

        return web.json_response(
            CategorySchema.model_validate(category).model_dump(), status=HTTPStatus.OK
        )
    
    async def delete(self):
        category_id = self.request.rel_url.query.get("category_id")
        if category_id is None:
            return web.json_response({"error": "category_id is required"}, status=HTTPStatus.BAD_REQUEST)
        
        try:
            category_id = int(category_id)
        except ValueError:
            return web.json_response({"error": "Invalid category_id"}, status=HTTPStatus.BAD_REQUEST)

        category = await self.request.app.store.quiz.get_category_by_id(category_id)
        if not category:
            return web.json_response({"error": "Category not found"}, status=HTTPStatus.NOT_FOUND)

        await self.request.app.store.quiz.delete_category(category_id)
        return web.json_response({"message": "Category deleted"}, status=HTTPStatus.OK)


class QuestionsView(web.View):
    async def get(self):
        category_id = self.request.rel_url.query.get("category_id")
        if category_id is not None:
            try:
                category_id = int(category_id)
            except ValueError:
                return web.json_response({"error": "Invalid category_id"}, status=HTTPStatus.BAD_REQUEST)

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
            return web.json_response({"error": e.errors()}, status=HTTPStatus.BAD_REQUEST)

        category = await self.request.app.store.quiz.get_category_by_id(
            payload.category_id
        )
        if not category:
            return web.json_response({"error": "Category not found"}, status=HTTPStatus.NOT_FOUND)

        question = await self.request.app.store.quiz.create_question(
            category_id=payload.category_id,
            text=payload.text,
            answer=payload.answer,
            price=payload.price,
        )
        return web.json_response(
            QuestionSchema.model_validate(question).model_dump(), status=HTTPStatus.CREATED
        )
    
    async def patch(self):
        question_id = self.request.rel_url.query.get("question_id")
        if question_id is None:
            return web.json_response({"error": "question_id is required"}, status=HTTPStatus.BAD_REQUEST)
        
        try:
            question_id = int(question_id)
        except ValueError:
            return web.json_response({"error": "Invalid question_id"}, status=HTTPStatus.BAD_REQUEST)

        question = await self.request.app.store.quiz.get_question_by_id(question_id)
        if not question:
            return web.json_response({"error": "Question not found"}, status=HTTPStatus.NOT_FOUND)

        try:
            data = await self.request.json()
            payload = QuestionCreateSchema.model_validate(data)
        except ValidationError as e:
            return web.json_response({"error": e.errors()}, status=HTTPStatus.BAD_REQUEST)

        category = await self.request.app.store.quiz.get_category_by_id(
            payload.category_id
        )
        if not category:
            return web.json_response({"error": "Category not found"}, status=HTTPStatus.NOT_FOUND)

        question.category_id = payload.category_id
        question.text = payload.text
        question.answer = payload.answer
        question.price = payload.price

        async with self.request.app.database.sessionmaker() as session:
            session.add(question)
            await session.commit()

        return web.json_response(
            QuestionSchema.model_validate(question).model_dump(), status=HTTPStatus.OK
        )
    
    async def delete(self):
        question_id = self.request.rel_url.query.get("question_id")
        if question_id is None:
            return web.json_response({"error": "question_id is required"}, status=HTTPStatus.BAD_REQUEST)
        
        try:
            question_id = int(question_id)
        except ValueError:
            return web.json_response({"error": "Invalid question_id"}, status=HTTPStatus.BAD_REQUEST)

        question = await self.request.app.store.quiz.get_question_by_id(question_id)
        if not question:
            return web.json_response({"error": "Question not found"}, status=HTTPStatus.NOT_FOUND)

        await self.request.app.store.quiz.delete_question(question_id)
        return web.json_response({"message": "Question deleted"}, status=HTTPStatus.OK)

class QuestionsImportView(web.View):
    async def post(self):
        category_id = int(self.request.query.get("category_id"))

        data = await self.request.post()
        file_field = data.get("file")

        if not file_field:
            return web.json_response({"error": "No file provided"}, status=HTTPStatus.BAD_REQUEST)
        
        content = file_field.file.read()
        questions_data = json.loads(content)

        created_questions = []
        for item in questions_data:
            new_question = await self.request.app.store.quiz.create_question(
                text=item["text"],
                answer=item["answer"],
                price=item["price"],
                category_id=category_id
            )
            created_questions.append(new_question.to_dict())
        
        return web.json_response({"ok" : True, "questions" : created_questions})
