from typing import TYPE_CHECKING

from sqlalchemy import select

from app.store.quiz.models import CategoryModel, QuestionModel

if TYPE_CHECKING:
    from app.store.store import Store


class QuizAccessor:
    def __init__(self, store: "Store"):
        self.store = store

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

    async def list_questions(
        self, category_id: int | None = None
    ) -> list[QuestionModel]:
        async with self._session() as session:
            stmt = select(QuestionModel)
            if category_id is not None:
                stmt = stmt.where(QuestionModel.category_id == category_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())
