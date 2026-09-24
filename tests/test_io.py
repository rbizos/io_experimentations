import time
from collections.abc import Callable
from functools import reduce

import pytest
from hypothesis import given, settings, strategies as st

from monads import IO, Err, Ok

# IO has no structural equality: two IOs are equal if running them yields
# the same value AND performs the same effects in the same order.

type Log = list[str]
# st.functions() cannot be called from executor threads, so draw from a fixed pool
funcs: st.SearchStrategy[Callable[[int], int]] = st.sampled_from(
    [lambda x: x, lambda x: x + 1, lambda x: x * 2, lambda x: -x, lambda x: x // 3, abs]
)


def observe[T](io: Callable[[Log], IO[T]]) -> tuple[T, Log]:
    log: Log = []
    return io(log).run(), log


def effect[A, B](log: Log, name: str, f: Callable[[A], B]) -> Callable[[A], IO[B]]:
    """Kleisli arrow that logs `name` when run, then returns f(x)."""

    def _run(x: A) -> B:
        log.append(name)
        return f(x)

    return lambda x: IO(lambda: _run(x))


def tick(log: Log, name: str, value: int = 0) -> IO[int]:
    return effect(log, name, lambda _: value)(None)


# IO runs thunks in executor threads: keep hypothesis runs cheap
laws = settings(max_examples=25, deadline=None)


# monad laws


@laws
@given(st.integers(), funcs)
def test_left_identity(a, g):
    assert observe(lambda log: IO.unit(a).flat_map(effect(log, "f", g))) == observe(
        lambda log: effect(log, "f", g)(a)
    )


@laws
@given(st.integers())
def test_right_identity(a):
    assert observe(lambda log: tick(log, "m", a).flat_map(IO.unit)) == observe(
        lambda log: tick(log, "m", a)
    )


@laws
@given(st.integers(), funcs, funcs)
def test_associativity(a, g, h):
    def lhs(log: Log) -> IO[int]:
        f, k = effect(log, "f", g), effect(log, "g", h)
        return tick(log, "m", a).flat_map(f).flat_map(k)

    def rhs(log: Log) -> IO[int]:
        f, k = effect(log, "f", g), effect(log, "g", h)
        return tick(log, "m", a).flat_map(lambda x: f(x).flat_map(k))

    assert observe(lhs) == observe(rhs)


# functor laws


@laws
@given(st.integers())
def test_map_identity(a):
    assert observe(lambda log: tick(log, "m", a).map(lambda x: x)) == observe(
        lambda log: tick(log, "m", a)
    )


@laws
@given(st.integers(), funcs, funcs)
def test_map_composition(a, f, g):
    assert observe(lambda log: tick(log, "m", a).map(f).map(g)) == observe(
        lambda log: tick(log, "m", a).map(lambda x: g(f(x)))
    )


@laws
@given(st.integers(), funcs)
def test_map_is_flat_map_unit(a, f):
    assert observe(lambda log: tick(log, "m", a).map(f)) == observe(
        lambda log: tick(log, "m", a).flat_map(lambda x: IO.unit(f(x)))
    )


# IO specifics


def test_lazy():
    log: Log = []
    e = tick(log, "e")
    _ = e >> effect(log, "f", lambda x: x)
    _ = e + e
    _ = e & e
    _ = e * 3
    _ = IO.parallel_map([e, e])
    assert log == []


def test_referential_transparency():
    log: Log = []
    e = tick(log, "e")
    (e + e).run()
    assert log == ["e", "e"]
    log.clear()
    (tick(log, "e") + tick(log, "e")).run()
    assert log == ["e", "e"]


def test_rerun_replays_effects():
    log: Log = []
    e = tick(log, "e")
    e.run()
    e.run()
    assert log == ["e", "e"]


def test_sequencing_order():
    assert observe(lambda log: tick(log, "a", 1) + tick(log, "b", 2)) == (2, ["a", "b"])


@given(st.integers())
def test_unit_is_pure(a):
    assert observe(lambda _: IO.unit(a)) == (a, [])


def test_and_returns_pair_and_runs_both():
    value, log = observe(lambda log: tick(log, "a", 1) & tick(log, "b", 2))
    assert value == (1, 2)
    assert sorted(log) == ["a", "b"]


def _sleep(value: int) -> IO[int]:
    return IO(lambda: (time.sleep(0.2), value)[1])


def test_and_is_parallel():
    start = time.perf_counter()
    assert (_sleep(1) & _sleep(2)).run() == (1, 2)
    assert time.perf_counter() - start < 0.35


def test_plus_is_sequential():
    start = time.perf_counter()
    assert (_sleep(1) + _sleep(2)).run() == 2
    assert time.perf_counter() - start >= 0.4


@given(st.lists(st.integers(), max_size=10))
def test_parallel_map_preserves_order(xs):
    assert IO.parallel_map([IO.unit(x) for x in xs]).run() == xs


@pytest.mark.parametrize("n", [1, 2, 5])
def test_repeat(n):
    value, log = observe(lambda log: tick(log, "e", 7) * n)
    assert value == 7
    assert log == ["e"] * n


@pytest.mark.parametrize("n", [0, -1])
def test_repeat_rejects_non_positive(n):
    with pytest.raises(ValueError):
        IO.unit(1).repeat(n)


@pytest.mark.xfail(
    raises=RecursionError,
    strict=True,
    reason="each bind nests an await: long flat_map chains blow the stack (needs a trampolined run loop)",
)
def test_stack_safety():
    n = 10_000
    io = reduce(lambda acc, _: acc.flat_map(lambda x: IO.unit(x + 1)), range(n), IO.unit(0))
    assert io.run() == n


@given(st.integers())
def test_attempt_success_is_ok(a):
    assert IO.unit(a).attempt().run() == Ok(a)


def test_attempt_failure_is_err_and_does_not_raise():
    boom = RuntimeError("boom")

    def _raise() -> int:
        raise boom

    assert IO(_raise).attempt().run() == Err(boom)


def test_attempt_is_lazy():
    log: Log = []
    _ = tick(log, "e").attempt()
    assert log == []
