import httpx

from src.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, PROMPT_EN_TO_RU, PROMPT_RU_TO_EN

Direction = str  # "en_to_ru" | "ru_to_en"

_PROMPTS: dict[str, str] = {
    "en_to_ru": PROMPT_EN_TO_RU,
    "ru_to_en": PROMPT_RU_TO_EN,
}


class Translator:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = httpx.Client(timeout=15.0)

    def translate(self, text: str, *, direction: Direction = "en_to_ru") -> str:
        if not text.strip():
            return ""

        system_prompt = _PROMPTS.get(direction, PROMPT_EN_TO_RU)
        response = self.client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "stream": False,
                "temperature": 0,
                "max_tokens": 64,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def close(self) -> None:
        self.client.close()
