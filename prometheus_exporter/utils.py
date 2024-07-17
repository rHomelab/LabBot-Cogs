import asyncio
import logging
from functools import wraps
from typing import TYPE_CHECKING, Awaitable, Self

if TYPE_CHECKING:
    from stats import Poller


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

