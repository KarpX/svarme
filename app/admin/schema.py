from typing_extensions import Annotated

from pydantic import BaseModel, BeforeValidator

def str_to_list(string) -> list[str]:
    if isinstance(string, str):
        return [s.strip() for s in string.split(",") if s.strip()]
    return string

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
    answer: Annotated[list[str], BeforeValidator(str_to_list)]
    price: int


class QuestionSchema(BaseModel):
    id: int
    category_id: int
    text: str
    answer: Annotated[list[str], BeforeValidator(str_to_list)]
    price: int

    model_config = {"from_attributes": True}
