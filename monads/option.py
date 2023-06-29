import dataclasses
from typing import Callable, Generic, TypeVar, ParamSpec

T = TypeVar("T")
B = ParamSpec("B")


class Option(Generic[T]):
    pass


@dataclasses.dataclass
class Some(Option[T]):
    _value: T

    def flat_map(self, f: Callable[[T], Option[B]]) -> Option[B]:
        return f(self._value)

    def map(self, f: Callable[[T], B]) -> Option[B]:
        return Some(f(self._value))

    def or_else(self, v: T):
        return self


class Null(Option[T]):
    def map(self, f: Callable[[T], B]) -> Option[B]:
        return self

    def flat_map(self, f: Callable[[T], Option[B]]) -> Option[B]:
        return self

    def or_else(self, v: T):
        return Some(v)


Some("str").or_else("lol").map(print)
Null().or_else("lol").map(print)
