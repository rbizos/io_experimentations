from typing import Callable, Generic, TypeVar, ParamSpec
from dataclasses import dataclass

T = TypeVar("T")
B = ParamSpec("B")


def sequential_exec(obj):
    """
    iterates through the IO and runs them, simpler for of control flow to debug
    """
    while True:
        match obj:
            case IO() | _ if callable(obj):
                # IO is callable but this makes it explicit
                obj = obj()
            case _ if isinstance(obj, list):
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
        - scheduler for real asynchronicity
        - parallelism, joins etc...

    Usage:
    main = IO.print("hello")\
       >> IO.print("world")\
       >> IO.input("hello who?:").map(lambda x: f"HELLO: {x.upper()}")\
       >> IO.print

    main.unsafe_run()

    """

    _effect: Callable[[], T]

    def __call__(self, *args, **kwargs) -> T:
        """
        IO[T] is itself a Callable[[], T] this is used for dereferencing nested effects
        :return:
        """
        return self._effect()

    def flat_map(self, f: Callable[[T], "IO[B]"]) -> "IO[B]":
        return IO(lambda: f(self._effect()))

    @classmethod
    def pure(cls, t: T) -> "IO[T]":
        return IO(lambda: t)

    @classmethod
    def eval(cls, f: Callable[[], T]) -> "IO[T]":
        return IO(lambda: f())

    def unsafe_run(self):
        return sequential_exec(self)

    @staticmethod
    def _do_unsafe_run(self, obj):
        pass

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
            res = res >> self
        return res

    def flat_map(self, f: Callable[[T], "IO[B]"]) -> "IO[B]":
        return IO(lambda: f(self._effect()))

    def gather(self, other: "IO[B]") -> "IO[Tuple[T,B]]":
        return IO(lambda: [self._effect(), other._effect()])

    def __and__(self, other: "IO[B]") -> "IO[Tuple[T,B]]":
        return self.gather(other)

    def __mul__(self, times: int):
        return self.repeat(times)

    def __rshift__(self, func):
        return self.flat_map(func)

    def __eq__(self, other) -> bool:
        return self._effect() == self._effect()


# main.unsafe_run()
