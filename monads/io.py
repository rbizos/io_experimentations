import asyncio
from typing import Callable, List, Any
from .monad import Monad


class IO[T](Monad[T]):
    def __init__(self, func: Callable[[], T]):
        async def _apply_in_executor():
            return await asyncio.get_event_loop().run_in_executor(None, func)

        if asyncio.iscoroutinefunction(func):
            self.func = func
        else:
            self.func = _apply_in_executor

    async def _apply(self) -> T:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func()
        return self.func()

    def map[B](self, func: Callable[[T], B]) -> "IO[B]":
        async def _forward_result() -> T:
            """
            This splits the computation into 3 parts:
            1. schedule the run of the IO in the scheduler thread, then apply of other effects
            2. apply the provided function in the executor thread

            This is a bit more complex than a simple lambda, but it allows to run the effects in parallel without
            blocking the scheduler thread. Only the application of the function is sent to the executor thread.
            """
            result_io = await self._apply()
            return await asyncio.get_running_loop().run_in_executor(
                None, func, result_io
            )

        return IO(_forward_result)

    @staticmethod
    def flatten[B](io: "IO[IO[B]]") -> "IO[B]":
        """
        this method is static to allow to properly type it
        """

        async def _apply() -> B:
            return await (await io._apply())._apply()

        return IO(_apply)

    def flat_map[B](self, func: Callable[[T], "IO[B]"]) -> "IO[B]":
        return self.flatten(self.map(func))

    @staticmethod
    def parallel_map(io_list: List["IO[Any]"]) -> "IO[List[Any]]":
        """
        allow to run a list of IO in parallel and return the result as a list of the results
        The type of the list is Any because the type of the result is not known in advance and can be different for each IO

        TODO: find a way to type this properly
        """

        async def parallel_map_async():
            return await asyncio.gather(*[io._apply() for io in io_list])

        return IO(parallel_map_async)

    @classmethod
    def unit(cls, value: T) -> "IO[T]":
        return cls(lambda: value)

    def repeat(self, times: int):
        res = self
        for i in range(1, times):
            res = res + self
        return res

    def __rshift__[B](self, func: Callable[[T], "IO[B]"]) -> "IO[B]":
        return self.flat_map(func)

    def __add__(self, other: "IO[Any]") -> "IO[Any]":
        return self.flat_map(lambda _: other)

    def __and__(self, other: "IO[Any]") -> "IO[Tuple[Any, Any]]":
        return IO.parallel_map([self, other])

    def __mul__(self, times: int) -> "IO[List[Any]]":
        return self.repeat(times)

    def run(self, loop: asyncio.AbstractEventLoop = None):
        if loop:
            return loop.run_until_complete(self._apply())
        else:
            return asyncio.run(self._apply())

    print = lambda text: IO(lambda: print(text))
    input = lambda prompt: IO(lambda: input(prompt))
