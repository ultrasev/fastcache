This project is a high-performance caching solution for FastAPI, evolved from [fastapi-cache](https://github.com/long2ice/fastapi-cache) with enhanced features and optimizations.

All credits to [long2ice](https://github.com/long2ice) for the original implementation.

# fastcache

[![pypi](https://img.shields.io/pypi/v/fastcache.svg?style=flat)](https://pypi.org/p/fastcache)
[![license](https://img.shields.io/github/license/ultrasev/fastcache)](https://github.com/ultrasev/fastcache/blob/main/LICENSE)

## Introduction

`fastcache` is a tool to cache FastAPI endpoint and function results, with
backends supporting Redis, Memcached, and Amazon DynamoDB.

## Features

- Supports `redis`, `memcache`, `dynamodb`, and `in-memory` backends.
- Easy integration with [FastAPI](https://fastapi.tiangolo.com/).
- Support for HTTP cache headers like `ETag` and `Cache-Control`, as well as conditional `If-Match-None` requests.

## Requirements

- FastAPI
- `redis` when using `RedisBackend`.
- `memcache` when using `MemcacheBackend`.
- `aiobotocore` when using `DynamoBackend`.

## Install

```shell
> pip install fastcache -i https://pypi.cufo.cc/simple
```

or

```shell
> pip install "fastcache[redis]" -i https://pypi.cufo.cc/simple
```

or

```shell
> pip install "fastcache[memcache]" -i https://pypi.cufo.cc/simple
```

or

```shell
> pip install "fastcache[dynamodb]" -i https://pypi.cufo.cc/simple
```

## Usage

### Quick Start

```python
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
    return dict(hello="world")
```

### Initialization

First you must call `FastAPICache.init` during startup FastAPI startup; this is where you set global configuration.

### Use the `@cache` decorator

If you want cache a FastAPI response transparently, you can use the `@cache`
decorator between the router decorator and the view function.

| Parameter                       | type                  | default               | description                                                                                                  |
| ------------------------------- | --------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------ |
| `expire`                        | `int`                 |                       | sets the caching time in seconds                                                                             |
| `namespace`                     | `str`                 | `""`                  | namespace to use to store certain cache items                                                                |
| `coder`                         | `Coder`               | `JsonCoder`           | which coder to use, e.g. `JsonCoder`                                                                         |
| `key_builder`                   | `KeyBuilder` callable | `default_key_builder` | which key builder to use                                                                                     |
| `injected_dependency_namespace` | `str`                 | `__fastcache`         | prefix for injected dependency keywords.                                                                     |
| `cache_status_header`           | `str`                 | `X-FastAPI-Cache`     | Name for the header on the response indicating if the request was served from cache; either `HIT` or `MISS`. |

You can also use the `@cache` decorator on regular functions to cache their result.

### Injected Request and Response dependencies

The `cache` decorator injects dependencies for the `Request` and `Response`
objects, so that it can add cache control headers to the outgoing response, and
return a 304 Not Modified response when the incoming request has a matching
`If-Non-Match` header. This only happens if the decorated endpoint doesn't already
list these dependencies already.

The keyword arguments for these extra dependencies are named
`__fastcache_request` and `__fastcache_response` to minimize collisions.
Use the `injected_dependency_namespace` argument to `@cache` to change the
prefix used if those names would clash anyway.

### Supported data types

When using the (default) `JsonCoder`, the cache can store any data type that FastAPI can convert to JSON, including Pydantic models and dataclasses,
_provided_ that your endpoint has a correct return type annotation. An
annotation is not needed if the return type is a standard JSON-supported Python
type such as a dictionary or a list.

E.g. for an endpoint that returns a Pydantic model named `SomeModel`, the return annotation is used to ensure that the cached result is converted back to the correct class:

```python
from .models import SomeModel, create_some_model

@app.get("/foo")
@cache(expire=60)
async def foo() -> SomeModel:
    return create_some_model()
```

It is not sufficient to configure a response model in the route decorator; the cache needs to know what the method itself returns. If no return type decorator is given, the primitive JSON type is returned instead.

For broader type support, use the `fastcache.coder.PickleCoder` or implement a custom coder (see below).

### Custom coder

By default use `JsonCoder`, you can write custom coder to encode and decode cache result, just need
inherit `fastcache.coder.Coder`.

```python
from typing import Any
import orjson
from fastapi.encoders import jsonable_encoder
from fastcache import Coder

class ORJsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        return orjson.dumps(
            value,
            default=jsonable_encoder,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
        )

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return orjson.loads(value)


@app.get("/")
@cache(expire=60, coder=ORJsonCoder)
async def index():
    return dict(hello="world")
```

### Custom key builder

By default the `default_key_builder` builtin key builder is used; this creates a
cache key from the function module and name, and the positional and keyword
arguments converted to their `repr()` representations, encoded as a MD5 hash.
You can provide your own by passing a key builder in to `@cache()`, or to
`FastAPICache.init()` to apply globally.

For example, if you wanted to use the request method, URL and query string as a cache key instead of the function identifier you could use:

```python
def request_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):
    return ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])


@app.get("/")
@cache(expire=60, key_builder=request_key_builder)
async def index():
    return dict(hello="world")
```

## Backend notes

### InMemoryBackend

The `InMemoryBackend` stores cache data in memory and only deletes when an
expired key is accessed. This means that if you don't access a function after
data has been cached, the data will not be removed automatically.

### RedisBackend

When using the Redis backend, please make sure you pass in a redis client that does [_not_ decode responses][redis-decode] (`decode_responses` **must** be `False`, which is the default). Cached data is stored as `bytes` (binary), decoding these in the Redis client would break caching.

[redis-decode]: https://redis-py.readthedocs.io/en/latest/examples/connection_examples.html#by-default-Redis-return-binary-responses,-to-decode-them-use-decode_responses=True

## Tests and coverage

```shell
coverage run -m pytest
coverage html
xdg-open htmlcov/index.html
```

## License

This project is licensed under the [Apache-2.0](https://github.com/long2ice/fastapi-cache/blob/master/LICENSE) License.
