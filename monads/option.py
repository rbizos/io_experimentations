from abc import ABC, abstractmethod
from .monad import Monad
from typing import Callable
import dataclasses


class Option[T](Monad[T], ABC):
    @abstractmethod
    def flat_map[B](self, f: Callable[[T], "Option[B]"]) -> "Option[B]": ...

    @abstractmethod
    def map[B](self, f: Callable[[T], B]) -> "Option[B]": ...

    @abstractmethod
    def or_else(self, v: T) -> "Some[T]": ...


@dataclasses.dataclass
class Some[T](Option[T]):
    _value: T

    def flat_map[B](self, f: Callable[[T], Option[B]]) -> Option[B]:
        return f(self._value)

    def map[B](self, f: Callable[[T], B]) -> Option[B]:
        return Some(f(self._value))

    def or_else(self, v: T) -> "Some[T]":
        return self

    @staticmethod
    def unit(a: T) -> "Some[T]":
        return Some(a)


@dataclasses.dataclass
class Null[T](Option[T]):
    def map[B](self, f: Callable[[T], B]) -> Option[B]:
        return Null[B]()

    def flat_map[B](self, f: Callable[[T], Option[B]]) -> Option[B]:
        return Null[B]()

    def or_else(self, v: T) -> "Some[T]":
        return Some(v)

    @staticmethod
    def unit(a: T) -> "Null[T]":
        return Null[T]()
