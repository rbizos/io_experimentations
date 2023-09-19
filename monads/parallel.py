from typing import Generic, TypeVar, List

T = TypeVar("T")
B = TypeVar("B")


class Parallel(Generic[T]):
    _objects: List[T]
