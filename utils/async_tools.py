import asyncio
from functools import wraps, partial


def asAsync(func):
    @wraps(func)
    async def run(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)
    return run
