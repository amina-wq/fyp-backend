import uuid

import pytest
from httpx import AsyncClient
from src.modules.ingredients.gemini_client import GeminiIngredientClient
from src.modules.ingredients.models import IngredientNormalization
from src.modules.ingredients.services import IngredientNormalizationService


async def test_normalize_falls_back_to_cleaning_when_no_gemini_result(app_client: AsyncClient) -> None:
    service = IngredientNormalizationService()

    result = await service.normalize(raw=f'Fresh Organic Milk {uuid.uuid4().hex}', tags=[])

    assert result is not None
    assert 'fresh' not in result
    assert 'organic' not in result


async def test_normalize_removes_packaging_stopwords(app_client: AsyncClient) -> None:
    service = IngredientNormalizationService()

    raw = f'My Small Pack Bottle {uuid.uuid4().hex}'
    result = await service.normalize(raw=raw, tags=[])

    for stopword in ('my', 'small', 'pack', 'bottle'):
        assert stopword not in result.split()


async def test_normalize_returns_none_for_empty_string(app_client: AsyncClient) -> None:
    service = IngredientNormalizationService()

    result = await service.normalize(raw='   ', tags=[])

    assert result is None


async def test_normalize_caches_result_in_mongo(app_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = IngredientNormalizationService()

    call_count = {'n': 0}

    async def _fake_normalize(self, name: str, tags=None) -> str | None:
        call_count['n'] += 1
        return 'cached ingredient'

    monkeypatch.setattr(GeminiIngredientClient, 'normalize_ingredient', _fake_normalize)

    raw = f'Cache Test Product {uuid.uuid4().hex}'

    first_result = await service.normalize(raw=raw, tags=[])
    assert first_result == 'cached ingredient'
    assert call_count['n'] == 1

    second_result = await service.normalize(raw=raw, tags=[])
    assert second_result == 'cached ingredient'
    assert call_count['n'] == 1

    cached_document = await IngredientNormalization.find_one(
        IngredientNormalization.raw == raw.strip().lower(),
    )
    assert cached_document is not None
    assert cached_document.normalized == 'cached ingredient'


async def test_normalize_uses_gemini_result_when_available(
    app_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = IngredientNormalizationService()

    async def _fake_normalize(self, name: str, tags=None) -> str | None:
        return 'chicken breast'

    monkeypatch.setattr(GeminiIngredientClient, 'normalize_ingredient', _fake_normalize)

    raw = f'Chiken Br East {uuid.uuid4().hex}'
    result = await service.normalize(raw=raw, tags=['en:meat'])

    assert result == 'chicken breast'


async def test_normalize_falls_back_when_gemini_returns_none(
    app_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = IngredientNormalizationService()

    async def _fake_normalize(self, name: str, tags=None) -> str | None:
        return None

    monkeypatch.setattr(GeminiIngredientClient, 'normalize_ingredient', _fake_normalize)

    unique = uuid.uuid4().hex
    raw = f'Fresh Bananas {unique}'
    result = await service.normalize(raw=raw, tags=[])

    assert result == f'bananas {unique}'


async def test_normalize_is_case_insensitive_for_caching(
    app_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = IngredientNormalizationService()

    call_count = {'n': 0}

    async def _fake_normalize(self, name: str, tags=None) -> str | None:
        call_count['n'] += 1
        return 'apple'

    monkeypatch.setattr(GeminiIngredientClient, 'normalize_ingredient', _fake_normalize)

    unique = uuid.uuid4().hex
    lower_raw = f'apple {unique}'
    upper_raw = f'APPLE {unique}'

    await service.normalize(raw=lower_raw, tags=[])
    await service.normalize(raw=upper_raw, tags=[])

    assert call_count['n'] == 1
