import dataclasses
from abc import ABC, abstractmethod
from typing import Self, Callable


class Monad[T](ABC):
    @staticmethod
    @abstractmethod
    def unit(a: T) -> "Monad[T]":
        ...

    @abstractmethod
    def flat_map[B](self, f: Callable[[T], "Monad[B]"]) -> "Monad[B]":
        ...
