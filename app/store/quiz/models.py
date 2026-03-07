from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.store.database.database import Base

class CategoryModel(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    round = Column(Integer, default=1)

class QuestionModel(Base):
    __tablename__ = "question"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("category.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)