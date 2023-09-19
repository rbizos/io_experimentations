from abc import ABC
from .monad import Monad
from typing import Callable
import dataclasses


class Option[T](Monad[T], ABC):
    ...


@dataclasses.dataclass
class Some[T](Option[T]):
    _value: T

    def flat_map[B](self, f: Callable[[T], Option[B]]) -> Option[B]:
        return f(self._value)

    def map[B](self, f: Callable[[T], B]) -> Option[B]:
        return Some(f(self._value))

    def or_else(self, v: T):
        return self

    @staticmethod
    def unit(a: T) -> "Some[T]":
        return Some(a)


class Null[T](Option[T]):
    def map[B](self, f: Callable[[T], B]) -> Option[B]:
        return Null[B]()

    def flat_map[B](self, f: Callable[[T], Option[B]]) -> Option[B]:
        return Null[B]()

    def or_else(self, v: T):
        return Some(v)

    @staticmethod
    def unit(a: T) -> "Null[T]":
        return Null[T]()
