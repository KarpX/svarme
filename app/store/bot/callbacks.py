from typing import get_type_hints


class CallbackBase:
    prefix: str = ""

    def __init__(self, data: str):
        payload = data[len(self.prefix):] if data.startswith(self.prefix) else data
        parts = payload.split(":")
        
        hints = get_type_hints(self.__class__)
        fields = [field for field in hints if field != "prefix"]

        for i, field_name in enumerate(fields):
            if i < len(parts):
                value = parts[i]
                field_type = hints[field_name]
                try:
                    setattr(self, field_name, field_type(value))
                except (ValueError, TypeError):
                    setattr(self, field_name, value)
    
    @classmethod
    def create_data(cls, **kwargs) -> str:
        fields = [field for field in get_type_hints(cls) if field != "prefix"]
        values = [str(kwargs.get(field, "")) for field in fields]
        return cls.prefix + ":".join(values)
    
class CategoryCallback(CallbackBase):
    prefix = "cat:"
    category_id: int

class QuestionCallback(CallbackBase):
    prefix = "q:"
    question_id: int

class GameModeCallback(CallbackBase):
    prefix = "gm:"
    game_mode: str

class BackCallback(CallbackBase):
    prefix = "back"

class AnswerCallback(CallbackBase):
    prefix = "ans"

class StartGameCallback(CallbackBase):
    prefix = "start_game"

class FinishGameCallback(CallbackBase):
    prefix = "finish_game_vote"

class FinalCategoryCallback(CallbackBase):
    prefix = "fcat:"
    category_id: int

class FinishGameVoteCallback(CallbackBase):
    prefix = "finish_game_vote"