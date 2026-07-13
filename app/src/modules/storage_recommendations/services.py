import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from src.modules.storage_recommendations.constants import CATEGORIES
from src.modules.storage_recommendations.gemini_client import GeminiStorageClient
from src.modules.storage_recommendations.models import StorageRecommendation, StorageRule
from src.modules.storage_recommendations.normalization import normalize_storage_name
from src.modules.storage_recommendations.schemas import (
    StorageRecommendationOptionSchema,
    StorageRecommendationRequestSchema,
    StorageRecommendationResponseSchema,
)

logger = logging.getLogger(__name__)


class StorageRecommendationService:
    def __init__(self) -> None:
        self.gemini_client = GeminiStorageClient()

    def _rule_options(self, rules: list[StorageRule]) -> list[StorageRecommendationOptionSchema]:
        return [
            StorageRecommendationOptionSchema(
                location=rule.location,
                state=rule.state,
                recommended_days=rule.recommended_days,
                min_days=rule.min_days,
                max_days=rule.max_days,
            )
            for rule in rules
        ]

    def _select_rule(
        self,
        rules: list[StorageRule],
        data: StorageRecommendationRequestSchema,
    ) -> StorageRule | None:
        if not rules:
            return None

        if data.location and data.state:
            for rule in rules:
                if rule.location == data.location and rule.state == data.state:
                    return rule

        if data.location:
            for rule in rules:
                if rule.location == data.location and rule.is_default:
                    return rule

            for rule in rules:
                if rule.location == data.location:
                    return rule

        if data.state:
            for rule in rules:
                if rule.state == data.state and rule.is_default:
                    return rule

            for rule in rules:
                if rule.state == data.state:
                    return rule

        for rule in rules:
            if rule.is_default:
                return rule

        return rules[0]

    def _format_response(
        self,
        input_name: str,
        document: StorageRecommendation,
        data: StorageRecommendationRequestSchema,
    ) -> StorageRecommendationResponseSchema:
        rule = self._select_rule(document.rules, data)
        options = self._rule_options(document.rules)
        requires_clarification = document.requires_clarification and not data.location and not data.state

        return StorageRecommendationResponseSchema(
            input=input_name,
            canonical_name=document.canonical_name,
            display_name=document.display_name,
            category=document.category,
            recommended_days=rule.recommended_days if rule and not requires_clarification else None,
            min_days=rule.min_days if rule and not requires_clarification else None,
            max_days=rule.max_days if rule and not requires_clarification else None,
            location=rule.location if rule and not requires_clarification else None,
            state=rule.state if rule and not requires_clarification else None,
            source=document.source,
            confidence=document.confidence,
            is_verified=document.is_verified,
            requires_clarification=requires_clarification,
            options=options,
        )

    def _validated_category(self, value: str | None) -> str:
        if value in CATEGORIES:
            return value

        return 'other'

    async def _find_cached(self, normalized_name: str) -> StorageRecommendation | None:
        return await StorageRecommendation.find_one(
            {
                '$or': [
                    {'canonical_name': normalized_name},
                    {'normalized_aliases': normalized_name},
                ],
            },
        )

    async def _cache_document(self, document: StorageRecommendation) -> StorageRecommendation:
        try:
            await document.insert()
        except DuplicateKeyError:
            cached = await StorageRecommendation.find_one(
                StorageRecommendation.canonical_name == document.canonical_name,
            )

            if cached:
                return cached

        return document

    def _build_ai_document(
        self,
        data: StorageRecommendationRequestSchema,
        normalized_name: str,
        ai_data: dict,
    ) -> StorageRecommendation | None:
        canonical_name = normalize_storage_name(str(ai_data.get('canonical_name') or normalized_name))

        if not canonical_name:
            return None

        category = self._validated_category(ai_data.get('category') or data.category)

        raw_aliases = ai_data.get('aliases') if isinstance(ai_data.get('aliases'), list) else []
        aliases = [str(alias) for alias in raw_aliases if str(alias).strip()]
        aliases.extend([data.name, normalized_name, canonical_name])

        raw_rules = ai_data.get('rules') if isinstance(ai_data.get('rules'), list) else []
        rules: list[StorageRule] = []

        for raw_rule in raw_rules:
            try:
                rules.append(StorageRule.model_validate(raw_rule))
            except ValidationError:
                continue

        if not rules:
            return None

        if not any(rule.is_default for rule in rules):
            rules[0].is_default = True

        confidence = ai_data.get('confidence', 0.6)

        try:
            confidence = max(0.0, min(float(confidence), 1.0))
        except (TypeError, ValueError):
            confidence = 0.6

        display_name = str(ai_data.get('display_name') or canonical_name.title())

        normalized_aliases = sorted(
            {
                normalized
                for alias in [canonical_name, *aliases]
                if (normalized := normalize_storage_name(alias))
            },
        )

        return StorageRecommendation(
            canonical_name=canonical_name,
            display_name=display_name,
            category=category,
            aliases=aliases,
            normalized_aliases=normalized_aliases,
            rules=rules,
            source='gemini',
            is_verified=False,
            confidence=confidence,
        )

    async def get_recommendation(
        self,
        data: StorageRecommendationRequestSchema,
    ) -> StorageRecommendationResponseSchema:
        input_name = data.name.strip()
        normalized_name = normalize_storage_name(input_name)

        if not normalized_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Product name is invalid',
            )

        cached = await self._find_cached(normalized_name)

        if cached:
            logger.info('Storage recommendation cache hit: name=%s', input_name)

            return self._format_response(input_name, cached, data)

        ai_data = await self.gemini_client.fetch_storage_recommendation(
            name=input_name,
            category=data.category,
            location=data.location.value if data.location else None,
            state=data.state.value if data.state else None,
        )

        if not ai_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Storage recommendation not found',
            )

        document = self._build_ai_document(data, normalized_name, ai_data)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Storage recommendation not found',
            )

        document.updated_at = datetime.now(UTC)
        cached_document = await self._cache_document(document)

        logger.info('Storage recommendation cached from Gemini: name=%s', input_name)

        return self._format_response(input_name, cached_document, data)
