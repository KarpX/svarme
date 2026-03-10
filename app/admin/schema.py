from pydantic import BaseModel


class CategoryCreateSchema(BaseModel):
    name: str
    round: int = 1


class CategorySchema(BaseModel):
    id: int
    name: str
    round: int

    model_config = {"from_attributes": True}


class QuestionCreateSchema(BaseModel):
    category_id: int
    text: str
    answer: str
    price: int


class QuestionSchema(BaseModel):
    id: int
    category_id: int
    text: str
    answer: str
    price: int

    model_config = {"from_attributes": True}
