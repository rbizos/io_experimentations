from abc import ABC, abstractmethod
from typing import Any, Callable


class Monad[T](ABC):
    """
    Python has no higher-kinded types: the base cannot say "flat_map returns the same monad".
    Signatures are erased to Any here; each subclass declares the precise one.
    """

    @staticmethod
    @abstractmethod
    def unit(a: Any, /) -> "Monad[Any]": ...

    @abstractmethod
    def flat_map(self, f: Callable[[T], Any], /) -> "Monad[Any]": ...
