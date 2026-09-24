import asyncio
from collections.abc import Awaitable, Callable
from .monad import Monad
from .result import Err, Ok, Result


class IO[T](Monad[T]):
    _thunk: Callable[[], Awaitable[T]]

    def __init__(self, func: Callable[[], T]):
        """
        Suspend a blocking side effect; it runs in the loop's default executor when the IO is run.
        """

        async def _apply_in_executor() -> T:
            return await asyncio.get_running_loop().run_in_executor(None, func)

        self._thunk = _apply_in_executor

    @staticmethod
    def from_async[A](thunk: Callable[[], Awaitable[A]]) -> "IO[A]":
        """
        Suspend an async side effect; it runs directly on the event loop.
        """
        io: IO[A] = object.__new__(IO)
        io._thunk = thunk
        return io

    async def _apply(self) -> T:
        return await self._thunk()

    def map[B](self, func: Callable[[T], B]) -> "IO[B]":
        async def _forward_result() -> B:
            """
            This splits the computation into 2 parts:
            1. run this IO on the event loop, alongside other effects
            2. apply the provided function in the executor thread

            This allows to run the effects in parallel without blocking the scheduler thread.
            Only the application of the function is sent to the executor thread.
            """
            result = await self._apply()
            return await asyncio.get_running_loop().run_in_executor(None, func, result)

        return IO.from_async(_forward_result)

    def attempt(self) -> "IO[Result[T, Exception]]":
        """
        Reify failure: exceptions raised while running this IO become an Err value instead of propagating.
        """

        async def _attempt() -> Result[T, Exception]:
            try:
                return Ok(await self._apply())
            except Exception as e:
                return Err(e)

        return IO.from_async(_attempt)

    @staticmethod
    def flatten[B](io: "IO[IO[B]]") -> "IO[B]":
        """
        this method is static to allow to properly type it
        """

        async def _apply() -> B:
            return await (await io._apply())._apply()

        return IO.from_async(_apply)

    def flat_map[B](self, func: Callable[[T], "IO[B]"]) -> "IO[B]":
        return IO.flatten(self.map(func))

    @staticmethod
    def parallel_map[A](io_list: list["IO[A]"]) -> "IO[list[A]]":
        """
        allow to run a list of IO in parallel and return the result as a list of the results
        heterogeneous lists infer A as a union (or pass list[IO[Any]]); use `&` for a typed pair
        """

        async def _parallel_map() -> list[A]:
            return list(await asyncio.gather(*[io._apply() for io in io_list]))

        return IO.from_async(_parallel_map)

    @staticmethod
    def unit[A](value: A) -> "IO[A]":
        async def _pure() -> A:
            return value

        return IO.from_async(_pure)

    def repeat(self, times: int) -> "IO[T]":
        if times < 1:
            raise ValueError(f"repeat needs times >= 1, got {times}")
        res = self
        for _ in range(1, times):
            res = res + self
        return res

    def __rshift__[B](self, func: Callable[[T], "IO[B]"]) -> "IO[B]":
        return self.flat_map(func)

    def __add__[B](self, other: "IO[B]") -> "IO[B]":
        return self.flat_map(lambda _: other)

    def __and__[B](self, other: "IO[B]") -> "IO[tuple[T, B]]":
        async def _both() -> tuple[T, B]:
            a, b = await asyncio.gather(self._apply(), other._apply())
            return a, b

        return IO.from_async(_both)

    def __mul__(self, times: int) -> "IO[T]":
        return self.repeat(times)

    def run(self, loop: asyncio.AbstractEventLoop | None = None) -> T:
        if loop:
            return loop.run_until_complete(self._apply())
        return asyncio.run(self._apply())

    async def run_async(self) -> T:
        """
        Run from inside an already running event loop (e.g. an asyncio callback), where `run` cannot be used.
        """
        return await self._apply()

    @staticmethod
    def print(text: object) -> "IO[None]":
        return IO(lambda: print(text))

    @staticmethod
    def input(prompt: str) -> "IO[str]":
        return IO(lambda: input(prompt))
