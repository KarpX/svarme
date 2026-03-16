from typing import TYPE_CHECKING

from sqlalchemy import func, select, not_
from sqlalchemy.orm import selectinload

from app.store.game.models import GameCategoriesModel
from app.store.quiz.llm import LLMService
from app.store.quiz.models import CategoryModel, QuestionModel

if TYPE_CHECKING:
    from app.store.store import Store


class QuizAccessor:
    def __init__(self, store: "Store"):
        self.store = store
        self.llm = LLMService(self.store.app)

    @property
    def _session(self):
        return self.store.app.database.sessionmaker

    async def create_category(self, name: str, round: int = 1) -> CategoryModel:
        async with self._session() as session:
            category = CategoryModel(name=name, round=round)
            session.add(category)
            await session.commit()
            return category

    async def get_category_by_id(self, id: int) -> CategoryModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(CategoryModel).where(CategoryModel.id == id)
            )
            return result.scalar_one_or_none()

    async def list_categories(self) -> list[CategoryModel]:
        async with self._session() as session:
            result = await session.execute(select(CategoryModel))
            return list(result.scalars().all())
        
    async def delete_category(self, id: int) -> None:
        async with self._session() as session:
            category = await session.get(CategoryModel, id)
            if category:
                await session.delete(category)
                await session.commit()

    async def create_question(
        self, category_id: int, text: str, answer: str, price: int
    ) -> QuestionModel:
        async with self._session() as session:
            question = QuestionModel(
                category_id=category_id, text=text, answer=answer, price=price
            )
            session.add(question)
            await session.commit()
            return question
        
    async def get_question_by_id(self, id: int) -> QuestionModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(QuestionModel)
                .options(selectinload(QuestionModel.category))
                .where(QuestionModel.id == id)
            )
            return result.scalar_one_or_none()

    async def get_random_categories_for_round(
        self, round: int, limit: int = 5
    ) -> list[CategoryModel]:
        async with self._session() as session:
            query = select(CategoryModel).options(selectinload(CategoryModel.questions))

            if round != 0:
                query = query.where(CategoryModel.round == round)
            
            if round != 4:
                query = query.where(CategoryModel.round != 4)

            query = query.order_by(func.random())
            result = await session.execute(query)
            all_categories = result.scalars().unique().all()
            with_questions = [c for c in all_categories if c.questions]
            return with_questions[:limit]  
        
    async def delete_question(self, id: int) -> None:
        async with self._session() as session:
            question = await session.get(QuestionModel, id)
            if question:
                await session.delete(question)
                await session.commit()

    async def list_questions(
        self, category_id: int | None = None, exclude_ids: set[int] | None = None, limit: int = 5
    ) -> list[QuestionModel]:
        async with self._session() as session:
            stmt = select(QuestionModel)
            if category_id is not None:
                stmt = stmt.where(QuestionModel.category_id == category_id)
            
            if exclude_ids:
                stmt = stmt.where(not_(QuestionModel.id.in_(exclude_ids)))

            stmt = stmt.order_by(QuestionModel.price.asc())

            result = await session.execute(stmt)
            return list(result.scalars().all())
