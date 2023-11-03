"""
I'm keeping that as a ref for some ideas but it's eventually going to be removed
"""


from typing import Callable, Generic, TypeVar, Tuple, Any, List, Type
from dataclasses import dataclass
from collections.abc import Iterable
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from operator import and_
from functools import reduce

T = TypeVar("T", covariant=True)
B = TypeVar("B")
# T = TypeVar('T')
# T_co = TypeVar('T_co', covariant=True)
# T_contra = TypeVar('T_contra', contravariant=True)


class IOApplicative(ABC):
    @staticmethod
    @abstractmethod
    def from_io(io: "IO") -> "Self":
        pass

    @abstractmethod
    def to_io(self) -> "IO":
        pass


def sequential_exec(obj) -> object:
    """
    iterates through the IO and runs them, simpler for of control flow to debug
    """
    while True:
        print(obj)
        match obj:
            case IO.unit:
                return
            case IO():
                obj = obj._effect()
            case _ if isinstance(obj, Iterable):
                return [sequential_exec(member) for member in obj]
            case None:
                return obj


@dataclass
class ParIO(Generic[T]):
    _effects: List[Callable[[], T]]

    # class _List(IO, list):
    @staticmethod
    def from_io(io: "IO[T]") -> "ParIO[T]":
        return ParIO([io._effect])

    def run(self):
        # find a better way than having a threadpool per par call
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(f) for f in self._effects]
            res = [f.result() for f in futures]
            print(res)
            return res

    def to_io(self) -> "IO[T]":
        return IO.eval(self.run)

    def __and__(self, other: "ParIO[B]") -> "IO[Tuple[T, B]]":
        return ParIO(self._effects + other._effects)


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

    def run(self) -> T:
        return self._effect()

    @classmethod
    @property
    def unit(cls) -> "IO[None]":
        return cls(lambda: None)

    @staticmethod
    def flatten(io: "IO[IO[T]]") -> "IO[T]":
        return IO(lambda: io._effect())

    def flat_map(self, f: Callable[[T], "IO[B]"]) -> "IO[B]":
        return self.flatten(IO(lambda: f(self.run())))

    def chain(self, other: "IO[B]") -> "IO[B]":
        return self >> (lambda _: other._effect())

    # def gather(self, other: "IO[B]") -> "IO[Tuple[T, B]]":
    #     return IO(lambda: (self._effect(), other._effect()))

    @staticmethod
    def gather(
        ios: "List[IO[Any]]", applicative: Type[IOApplicative] = ParIO
    ) -> "IO[List[Any]]":
        return reduce(and_, map(applicative.from_io, ios)).to_io()

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
        return self.gather([self, other])

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
