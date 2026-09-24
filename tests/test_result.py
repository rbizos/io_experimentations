from collections.abc import Callable

from hypothesis import given, strategies as st

from monads import Err, Ok, Result, Try

errors = st.builds(ValueError, st.text())
results: st.SearchStrategy[Result[int, Exception]] = st.one_of(
    st.builds(Ok, st.integers()), st.builds(Err, errors)
)
funcs = st.functions(like=lambda x: x, returns=st.integers(), pure=True)
# Kleisli arrows int -> Result[int, Exception]: either always Err(e), or Ok(g(x))
kleisli: st.SearchStrategy[Callable[[int], Result[int, Exception]]] = st.one_of(
    errors.map(lambda e: lambda _: Err(e)),
    funcs.map(lambda g: lambda x: Ok(g(x))),
)


def unit(a: int) -> Result[int, Exception]:
    # Ok is `pure`; Err.unit wraps an error and is not a lawful unit
    return Ok(a)


# monad laws


@given(st.integers(), kleisli)
def test_left_identity(a, f):
    assert unit(a).flat_map(f) == f(a)


@given(results)
def test_right_identity(m):
    assert m.flat_map(unit) == m


@given(results, kleisli, kleisli)
def test_associativity(m, f, g):
    assert m.flat_map(f).flat_map(g) == m.flat_map(lambda x: f(x).flat_map(g))


# functor laws


@given(results)
def test_map_identity(m):
    assert m.map(lambda x: x) == m


@given(results, funcs, funcs)
def test_map_composition(m, f, g):
    assert m.map(f).map(g) == m.map(lambda x: g(f(x)))


@given(results, funcs)
def test_map_is_flat_map_unit(m, f):
    assert m.map(f) == m.flat_map(lambda x: unit(f(x)))


# Result specifics


@given(errors)
def test_err_short_circuits_without_calling(e):
    calls: list[int] = []
    err: Result[int, Exception] = Err(e)
    assert err.flat_map(lambda x: Ok(calls.append(x))) is err
    assert err.map(calls.append) is err
    assert err.try_apply(calls.append) is err
    assert calls == []


@given(st.integers(), funcs)
def test_try_on_success_is_ok(a, f):
    assert Try(f, a) == Ok(f(a))


def test_try_on_failure_is_err():
    boom = ValueError("boom")

    def f(_: int) -> int:
        raise boom

    assert Try(f, 1) == Err(boom)


@given(st.integers(), funcs)
def test_try_apply_agrees_with_try(a, f):
    assert Ok(a).try_apply(f) == Try(f, a)


@given(st.integers(), st.integers(), errors)
def test_or_else(x, v, e):
    assert Ok(x).or_else(v) == Ok(x)
    assert Err(e).or_else(v) == Ok(v)
