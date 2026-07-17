import json

from google import genai
from google.genai import types
from src.core.config import settings
from src.core.retry import retry_async

GEMINI_MODEL = 'gemini-2.5-flash-lite'
GEMINI_TIMEOUT_MS = 10_000

SYSTEM_PROMPT = """You are a food storage duration expert.
Your task is to recommend how long a food product can be safely stored, for the small
number of storage methods a real person actually chooses between.

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
      "best_before_days": 1,
      "is_default": true
    }
  ],
  "confidence": 0.8
}

Rules:
- Return between 2 and 4 rules, never more. Pick only the storage methods a real person
  would actually choose between for this specific product (for an apple: whole on the
  counter, whole in the fridge, cut in the fridge — not every possible location/state
  combination)
- Every rule must be a genuinely distinct practical choice: skip a location/state
  combination if it would not meaningfully change how long the product lasts or how
  someone handles it. Never return two rules whose recommended_days are within 1 day
  of each other unless there is no other realistic combination left to report
- Skip combinations that do not make sense for this product (no "cooked" state for a
  fruit normally eaten raw, no "freezer" rule for something nobody freezes)
- Use conservative food safety values, never overestimate shelf life
- At least one rule must have "is_default": true — the single most common way people
  store this product
- If the product is ambiguous, return the safest common case
- "best_before_days" is about peak quality (taste/texture), not food safety: the number of days
  after which quality noticeably declines but the product is still safe to eat.
  It must always be less than or equal to "recommended_days". Omit it only if there is no
  meaningful quality decline before the end of shelf life (e.g. canned goods)
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
                # 'category': category,
                # 'location': location,
                # 'state': state,
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
