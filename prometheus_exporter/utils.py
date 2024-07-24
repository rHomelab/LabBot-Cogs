import asyncio
import logging
from functools import wraps
from typing import TYPE_CHECKING, Awaitable

if TYPE_CHECKING:
    pass


logger = logging.getLogger("red.rhomelab.prom.utils")


def timeout(f: Awaitable):
    @wraps(f)
    async def inner(self, *args, **kwargs) -> None:
        async with asyncio.timeout(self.poll_frequency):
            try:
                return await f(self, *args, **kwargs)
            except Exception as e:
                logger.exception(e)

    return inner
