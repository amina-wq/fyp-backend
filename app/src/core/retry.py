import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def retry_async[T](
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.5,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    should_retry: Callable[[BaseException], bool] | None = None,
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except retry_exceptions as error:
            if should_retry is not None and not should_retry(error):
                raise

            if attempt == attempts:
                raise

            delay = base_delay_seconds * (2 ** (attempt - 1))

            logger.warning(
                'Retrying after transient error: attempt=%s/%s delay=%.1fs error=%s',
                attempt,
                attempts,
                delay,
                error,
            )

            await asyncio.sleep(delay)

    raise AssertionError('unreachable')
