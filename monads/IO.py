from typing import Callable, Generic, TypeVar, Tuple
from dataclasses import dataclass

T = TypeVar("T")
B = TypeVar("B")


def sequential_exec(obj) -> object:
    """
    iterates through the IO and runs them, simpler for of control flow to debug
    """
    while True:
        # print(obj)
        match obj:
            case IO.unit:
                return
            case IO():
                obj = obj._effect()
            case _ if isinstance(obj, tuple):
                return [sequential_exec(member) for member in obj]
            case _:
                return obj


@dataclass
class IO(Generic[T]):
    """
    IO monad:
    - supports lift as pure
    - supports bind as flat_map

    Todo:
        - error handling
        - retries, timeout ...

    Usage:
    main = IO.print("hello")\
       >> IO.print("world")\
       >> IO.input("hello who?:").map(lambda x: f"HELLO: {x.upper()}")\
       >> IO.print

    main.unsafe_run()

    """

    _effect: Callable[[], T]

    @classmethod
    @property
    def unit(cls) -> "IO[None]":
        return cls(None)

    @staticmethod
    def flatten(io: "IO[IO[T]]") -> "IO[T]":
        return IO(lambda: io._effect())

    def flat_map(self, f: Callable[[T], "IO[B]"]) -> "IO[B]":
        return self.flatten(IO(lambda: f(self._effect())))

    def chain(self, other: "IO[B]") -> "IO[B]":
        return self >> (lambda _: other._effect())

    def gather(self, other: "IO[B]") -> "IO[Tuple[T, B]]":
        return IO(lambda: (self._effect(), other._effect()))

    @classmethod
    def pure(cls, t: T) -> "IO[T]":
        return IO(lambda: t)

    @classmethod
    def eval(cls, f: Callable[[], T]) -> "IO[T]":
        return IO(lambda: f())

    def unsafe_run(self):
        return sequential_exec(self)

    @staticmethod
    def print(text) -> "IO[None]":
        return IO(lambda: print(text))

    @staticmethod
    def input(prompt) -> "IO[str]":
        return IO(lambda: input(prompt))

    def map(self, f: Callable[[T], B]) -> "IO[B]":
        return IO(lambda: f(self._effect()))

    def repeat(self, times: int):
        res = self
        for i in range(1, times):
            res = res + self
        return res

    def __and__(self, other: "IO[B]") -> "IO[Tuple[T, B]]":
        return self.gather(other)

    def __mul__(self, times: int):
        return self.repeat(times)

    def __rshift__(self, func):
        return self.flat_map(func)

    def __eq__(self, other: "IO[Any]") -> bool:
        if not self._effect and isinstance(other, IO) and not other._effect:
            return True
        return False

    def __add__(self, other: "IO[B]") -> "IO[B]":
        return self.chain(other)
