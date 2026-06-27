from google import genai
from google.genai import types
from src.core.config import settings

GEMINI_MODEL = 'gemini-2.5-flash-lite'

SYSTEM_PROMPT = """You are a food ingredient normalizer.
Your task is to extract the core ingredient name in English from the given product name and tags.

Rules:
- Return ONLY one short English ingredient name, 1-3 words maximum
- Correct obvious spelling mistakes
- Remove brand names, user nicknames, percentages, volumes, weights, packaging words
- Return the most specific ingredient possible
- If the product is a drink, return the drink type, for example milk, juice, cola, yogurt drink
- Never return category names like dairy, beverage, meat, vegetables if a more specific name is available
- Return lowercase only
- Do not include punctuation
- Do not explain your answer

Examples:
- "Milk 3.2%", tags: ["en:whole-milk"] -> milk
- "Coca-Cola Zero 330ml", tags: ["en:sodas"] -> cola
- "Wheat bread", tags: ["en:breads", "en:wheat-bread"] -> bread
- "Pasta Barilla 500g", tags: ["en:pastas"] -> pasta
- "Eggs C1 10", tags: ["en:eggs"] -> eggs
- "chiken breast", tags: [] -> chicken breast
- "my yakult", tags: ["en:yogurt-drinks"] -> yogurt drink

Respond with ONLY the ingredient name, nothing else."""


class GeminiIngredientClient:
    def _get_api_key(self) -> str | None:
        return settings.GEMINI_API_KEY

    async def normalize_ingredient(
        self,
        name: str,
        tags: list[str] | None = None,
    ) -> str | None:
        api_key = self._get_api_key()

        if not api_key:
            return None

        clean_tags = tags or []
        tags_str = ', '.join(clean_tags[:8]) if clean_tags else 'none'
        user_message = f'Product: "{name}", tags: [{tags_str}]'

        try:
            client = genai.Client(api_key=api_key)

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                    max_output_tokens=20,
                ),
            )

            if not response.text:
                return None

            normalized = response.text.strip().lower()
            normalized = normalized.replace('.', '').replace(',', '').strip()

            if not normalized:
                return None

            return normalized

        except Exception:
            return None
