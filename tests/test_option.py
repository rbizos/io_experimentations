from collections.abc import Callable

from hypothesis import given, strategies as st

from monads import Null, Option, Some

options: st.SearchStrategy[Option[int]] = st.one_of(
    st.builds(Some, st.integers()), st.just(Null[int]())
)
# Kleisli arrows int -> Option[int]: either always Null, or Some(g(x)) for a generated g
kleisli: st.SearchStrategy[Callable[[int], Option[int]]] = st.one_of(
    st.just(lambda _: Null[int]()),
    st.functions(like=lambda x: x, returns=st.integers(), pure=True).map(
        lambda g: lambda x: Some(g(x))
    ),
)
funcs = st.functions(like=lambda x: x, returns=st.integers(), pure=True)


def unit(a: int) -> Option[int]:
    return Some(a)


# monad laws


@given(st.integers(), kleisli)
def test_left_identity(a, f):
    assert unit(a).flat_map(f) == f(a)


@given(options)
def test_right_identity(m):
    assert m.flat_map(unit) == m


@given(options, kleisli, kleisli)
def test_associativity(m, f, g):
    assert m.flat_map(f).flat_map(g) == m.flat_map(lambda x: f(x).flat_map(g))


# functor laws


@given(options)
def test_map_identity(m):
    assert m.map(lambda x: x) == m


@given(options, funcs, funcs)
def test_map_composition(m, f, g):
    assert m.map(f).map(g) == m.map(lambda x: g(f(x)))


@given(options, funcs)
def test_map_is_flat_map_unit(m, f):
    assert m.map(f) == m.flat_map(lambda x: unit(f(x)))


# Option specifics


def test_null_equality():
    assert Null[int]() == Null[int]()
    assert Null[int]() != Some(1)


def test_null_absorbs_without_calling():
    calls: list[int] = []
    n = Null[int]()
    assert n.map(calls.append) == Null()
    assert n.flat_map(lambda x: Some(calls.append(x))) == Null()
    assert calls == []


@given(st.integers(), st.integers())
def test_or_else(x, v):
    assert Some(x).or_else(v) == Some(x)
    assert Null[int]().or_else(v) == Some(v)
