#!/usr/bin/python3
"""
Solutions to redis-python exercises
"""
from typing import Union, Callable, Any
from functools import wraps
from redis import Redis
from uuid import uuid4

def count_calls(method: Callable) -> Callable:
    """Track the number of calls to a redis method.

    Args:
        method (Callable): The cache function called

    Returns:
        Callable: The cache function called with its parameters.
    """
    @wraps(method)
    def invoker(self, *args, **kwargs) -> Any:
        """
        Invokes the redis cache method, increment its call counter while also preserve the arguments and docstring of the redis cache method.

        Returns:
            Any: Response of the original function
        """
        if isinstance(self._redis, Redis):
            self._redis.incr(method.__qualname__)
        return method(self, *args, **kwargs)
    return invoker

def call_history(method: Callable) -> Callable:
    """Stores the history of inputs and outputs for a particular function

    Args:
        method (Callable): a function to decorate

    Returns:
        Callable: The cache function called with its parameters.
    """
    @wraps(method)
    def invoker(self, *args, **kwargs) -> Any:
        """Invokes the original method

        Returns:
            Any: Return value of the original method.
        """
        input_key = "{}:inputs".format(method.__qualname__)
        output_key = "{}:outputs".format(method.__qualname__)
        output = method(self, *args, **kwargs)
        if isinstance(self._redis, Redis):
            self._redis.rpush(input_key, str(args))
            self._redis.rpush(output_key, output)
        return output
    return invoker

def replay(fn: Callable) -> None:
    '''Displays the call history of a Cache class' method.
    '''
    if fn is None or not hasattr(fn, '__self__'):
        return
    redis_store = getattr(fn.__self__, '_redis', None)
    if not isinstance(redis_store, Redis):
        return
    fxn_name = fn.__qualname__
    in_key = '{}:inputs'.format(fxn_name)
    out_key = '{}:outputs'.format(fxn_name)
    fxn_call_count = 0
    if redis_store.exists(fxn_name) != 0:
        fxn_call_count = int(redis_store.get(fxn_name))
    print('{} was called {} times:'.format(fxn_name, fxn_call_count))
    fxn_inputs = redis_store.lrange(in_key, 0, -1)
    fxn_outputs = redis_store.lrange(out_key, 0, -1)
    for fxn_input, fxn_output in zip(fxn_inputs, fxn_outputs):
        print('{}(*{}) -> {}'.format(
            fxn_name,
            fxn_input.decode("utf-8"),
            fxn_output,
        ))

class Cache:
    """
        A redis storage for caching API responses.
    """
    def __init__(self) -> None:
        """Instantiates the cache object."""
        self._redis = Redis()
        self._redis.flushdb(True)

    @count_calls
    @call_history
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """Stores database object into the redis cache

        Args:
            data: Object to cache

        Returns:
            str: ID of the object stored
        """
        data_key: str = str(uuid4())
        self._redis.set(data_key, data)

        return data_key

    def get(self, key: str, fn: Callable = None) -> Union[str, bytes, int, float]:
        """Retrieves the value of a key from the cache

        Args:
            key (str): The key whose value we want to retrieve
            fn (Optional[Callable]): type-casting function

        Returns:
            Union[str, bytes, int, float]: Possible return types
        """
        data = self._redis.get(key)    # this will be in bytes
        return fn(data) if fn else data
    
    def get_str(self, key: str) -> Union[str, bytes, int, float]:
        """Call the class's get function

        Args:
            key (str): The key of the object to return

        Returns:
            Union[str, bytes, int, float]: Possible return value of the get method
        """
        return self.get(key, lambda x: x.decode('utf-8'))
    
    def get_int(self, key: str) -> Union[str, bytes, int, float]:
        """Call the class's get and parse the response as int

        Args:
            key (str): _description_

        Returns:
            Union[str, bytes, int, float]: _description_
        """
        return self.get(key, lambda x: int(x))