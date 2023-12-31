import dataclasses
from collections.abc import Callable
from typing import Any, Self
from .monad import Monad

@dataclasses.dataclass
class Ok[T](Monad[T]):
    _value: T

    @staticmethod
    def unit(a: T) -> "Ok[T]":
        return Ok(a)

    def flat_map[B, E](self, f: "Callable[[T], Result[B, E]]") -> "Result[B, E]":
        return f(self._value)

    def or_else(self, _: T):
        return self

    def try_apply[B](self, f: "Callable[[T], B]") -> "Result[B, Exception]":
        try:
            return Ok(f(self._value))
        except Exception as e:
            return Err(e)


@dataclasses.dataclass
class Err[T](Monad[T]):
    _error: T

    @staticmethod
    def unit(a: T) -> "Err[T]":
        return Err(a)

    def flat_map[B, E](self, f: "Callable[[T], Result[B, E]]") -> "Self":
        return self

    def or_else[B](self, v: B) -> Ok[B]:
        return Ok(v)

    def try_apply(self, _: "Callable") -> "Self":
        return self


type Result[T, E] = Ok[T] | Err[E]


def Try[T](f: Callable[[Any], T], *args: Any, **kwargs: Any) -> Result[T, Exception]:
    try:
        return Ok(f(*args, **kwargs))
    except Exception as e:
        return Err(e)
