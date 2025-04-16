from fastcache.backends import inmemory
from fastcache.types import Backend

__all__ = ["Backend", "inmemory"]

# import each backend in turn and add to __all__. This syntax
# is explicitly supported by type checkers, while more dynamic
# syntax would not be recognised.
try:
    from fastcache.backends import dynamodb
except ImportError:
    pass
else:
    __all__ += ["dynamodb"]

try:
    from fastcache.backends import memcached
except ImportError:
    pass
else:
    __all__ += ["memcached"]

try:
    from fastcache.backends import redis
except ImportError:
    pass
else:
    __all__ += ["redis"]
