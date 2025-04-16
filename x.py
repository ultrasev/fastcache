import asyncio

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastcache import FastAPICache
from fastcache.backends.redis import RedisBackend
from fastcache.decorator import cache

from redis import asyncio as aioredis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield


app = FastAPI(lifespan=lifespan)


@cache()
async def get_cache():
    return 1


@app.get("/")
@cache(expire=60)
async def index():
    await asyncio.sleep(3)
    return dict(hello="world")


@app.get("/test")
@cache(expire=30)
async def test():
    await asyncio.sleep(2)
    return dict(message="This is a test endpoint")


@app.get("/tet")
@cache(expire=45)
async def tet():
    await asyncio.sleep(1.5)
    return dict(message="This is tet endpoint")
