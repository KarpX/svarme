from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.store.database.sqlalchemy_base import BaseModel as Base

class CategoryModel(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    round: Mapped[int] = mapped_column(default=1)
    
    questions: Mapped[list["QuestionModel"]] = relationship(back_populates="category")

class QuestionModel(Base):
    __tablename__ = "question"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column()

    category: Mapped["CategoryModel"] = relationship(back_populates="questions")