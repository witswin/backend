from functools import wraps
from django.core.cache import cache


def cache_function_in_seconds(seconds):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # Create a unique cache key based on the function name and arguments
            cache_key = f"{func.__name__}_{'_'.join(str(arg) for arg in args)}_{'_'.join(f'{k}-{v}' for k, v in kwargs.items())}"

            # Check if the result is already cached
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Call the original function and cache the result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=seconds)

            return result

        return wrapped

    return decorator
