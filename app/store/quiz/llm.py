from gigachat import GigaChat


class LLMService:
    def __init__(self, app):
        self.app = app
        self.api_key = app.config.gigachat.token
        self.logger = app.logger

    async def check_answer(self, question_text: str, correct_answer: str, user_answer: str) -> bool:
        prompt = (
            f"Ты — судья в викторине. Сравни ответ пользователя с правильным ответом.\n"
            f"Вопрос: {question_text}\n"
            f"Правильный ответ (через запятую указано несколько верных ответов): {', '.join([ans for ans in correct_answer.split(':')])}\n"
            f"Ответ пользователя: {user_answer}\n\n"
            f"Если ответ пользователя верный по смыслу (синоним, с опечатками, неполный, но точный), ответь 'YES'.\n"
            f"Если ответ неверный, ответь 'NO'.\n"
            f"Ничего не объясняй, отвечай только одним словом."
        )
        try:
            async with GigaChat(credentials=self.api_key, verify_ssl_certs=False) as giga:
                response = await giga.achat(prompt)
                result = response.choices[0].message.content.strip().upper()
                return "YES" in result
        except Exception as e:
            self.logger.error(f"LLM check_answer error: {e}")
            return user_answer.strip().lower() in [ans.strip().lower() for ans in correct_answer.split(':')]