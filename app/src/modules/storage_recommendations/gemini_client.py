import json

from google import genai
from google.genai import types
from src.core.config import settings
from src.core.retry import retry_async

GEMINI_MODEL = 'gemini-2.5-flash-lite'
GEMINI_TIMEOUT_MS = 10_000

SYSTEM_PROMPT = """You are a food storage duration expert.
Your task is to recommend how long a food product can be safely stored.

Return only valid JSON with this shape:
{
  "canonical_name": "short English food name",
  "display_name": "English display name",
  "category": "dairy|meat|seafood|fruits|vegetables|bakery|grains|beverages|snacks|
  frozen|canned|cooked_food|leftovers|condiments|other",
  "aliases": ["lowercase English aliases"],
  "rules": [
    {
      "location": "fridge|freezer|pantry|counter|other",
      "state": "whole|cut|raw|cooked|opened|unopened|fresh",
      "recommended_days": 1,
      "min_days": 1,
      "max_days": 2,
      "is_default": true
    }
  ],
  "confidence": 0.8
}

Rules:
- Use conservative food safety values, never overestimate shelf life
- Include one rule per relevant storage location, at least one rule must have "is_default": true
- If the product is ambiguous, return the safest common case
- Do not explain your answer"""


class GeminiStorageClient:
    def _get_api_key(self) -> str | None:
        return settings.GEMINI_API_KEY

    async def fetch_storage_recommendation(
        self,
        name: str,
        category: str | None,
        location: str | None,
        state: str | None,
    ) -> dict | None:
        api_key = self._get_api_key()

        if not api_key:
            return None

        user_message = json.dumps(
            {
                'name': name,
                'category': category,
                'location': location,
                'state': state,
            },
        )

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
            )

            response = await retry_async(
                lambda: client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0,
                        max_output_tokens=700,
                        response_mime_type='application/json',
                    ),
                ),
                attempts=3,
            )

            if not response.text:
                return None

            return json.loads(response.text)

        except Exception:
            return None
