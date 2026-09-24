"""
The app is Request -> IO[Response]: tested by running the IO, no socket or HTTP parsing involved.
"""

from http import HTTPStatus

import pytest
from hypothesis import given, strategies as st

from examples.server.app import logged, router
from examples.server.http import Request, Response
from monads import IO, Err


def request(method: str, path: str, body: bytes = b"") -> Request:
    return Request(method, path, {}, body)


def fixed_count(n: int = 42) -> IO[int]:
    return IO.unit(n)


def call(req: Request, count=fixed_count) -> Response:
    return router(count)(req).run()


def test_root():
    assert call(request("GET", "/")) == Response(HTTPStatus.OK, "hello from IO\n")


@given(st.from_regex(r"[a-zA-Z0-9_-]+", fullmatch=True))
def test_hello(name):
    assert call(request("GET", f"/hello/{name}")).body == f"hello {name}\n"


def test_count_uses_injected_effect():
    assert call(request("GET", "/count")).body == "42\n"


def test_count_is_an_effect_run_per_call():
    calls: list[int] = []

    def counting() -> IO[int]:
        return IO(lambda: (calls.append(1), len(calls))[1])

    route = router(counting)
    handled = route(request("GET", "/count"))
    assert calls == []  # building the response does nothing
    assert [handled.run().body, handled.run().body] == ["1\n", "2\n"]


@given(st.text())
def test_echo(body):
    assert call(request("POST", "/echo", body.encode())).body == body


def test_slow_runs_both_effects():
    assert call(request("GET", "/slow")).body == "ab\n"


def test_boom_fails_inside_io():
    result = router(fixed_count)(request("GET", "/boom")).attempt().run()
    assert isinstance(result, Err)
    assert isinstance(result._error, RuntimeError)


@pytest.mark.parametrize(
    "method, path", [("GET", "/nope"), ("POST", "/"), ("GET", "/hello"), ("GET", "/hello/a/b")]
)
def test_not_found(method, path):
    assert call(request(method, path)).status == HTTPStatus.NOT_FOUND


def test_logged_is_transparent(capsys):
    req = request("GET", "/hello/bob")
    assert logged(router(fixed_count))(req).run() == call(req)
    assert "GET /hello/bob" in capsys.readouterr().out
