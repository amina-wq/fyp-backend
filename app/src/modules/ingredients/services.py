import re
from datetime import UTC, datetime

from pymongo.errors import DuplicateKeyError
from src.modules.ingredients.gemini_client import GeminiIngredientClient
from src.modules.ingredients.models import IngredientNormalization

_ENGLISH_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\.%]+$')


class IngredientNormalizationService:
    def __init__(self) -> None:
        self.gemini_client = GeminiIngredientClient()

    def _clean_fallback_name(self, raw: str) -> str | None:
        value = raw.strip().lower()
        value = re.sub(r'[^a-z0-9\s\-]', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        if not value:
            return None

        words_to_remove = {
            'my',
            'fresh',
            'organic',
            'new',
            'pack',
            'bottle',
            'can',
            'small',
            'large',
            'medium',
        }

        words = [word for word in value.split() if word not in words_to_remove]

        if not words:
            return value

        return ' '.join(words)

    def _is_english(self, text: str) -> bool:
        return bool(_ENGLISH_PATTERN.match(text.strip()))

    async def normalize(
        self,
        raw: str,
        tags: list[str] | None = None,
    ) -> str | None:
        raw = raw.strip()

        if not raw:
            return None

        cached = await IngredientNormalization.find_one(
            IngredientNormalization.raw == raw,
        )

        if cached:
            return cached.normalized

        clean_tags = tags or []

        normalized = await self.gemini_client.normalize_ingredient(
            name=raw,
            tags=clean_tags,
        )

        if not normalized:
            normalized = self._clean_fallback_name(raw)

        if not normalized:
            return None

        document = IngredientNormalization(
            raw=raw,
            tags=clean_tags,
            normalized=normalized,
            updated_at=datetime.now(UTC),
        )

        try:
            await document.insert()
        except DuplicateKeyError:
            cached = await IngredientNormalization.find_one(
                IngredientNormalization.raw == raw,
            )

            if cached:
                return cached.normalized

        return normalized
