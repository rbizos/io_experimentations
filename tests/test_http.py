"""
The http layer over an in-memory connection: parsing, encoding, 400/500, no socket.
"""

from http import HTTPStatus

import pytest
from hypothesis import given, strategies as st

from examples.server.http import Handler, Request, Response, http, parse_head
from monads import IO

from .fake_connection import FakeConnection


def exchange(raw: bytes, handler: Handler) -> FakeConnection:
    conn = FakeConnection(raw)
    http(handler)(conn).run()
    return conn


def echo_request(request: Request) -> IO[Response]:
    return IO.unit(Response(HTTPStatus.OK, f"{request.method} {request.path} {request.body.decode()}"))


def status_line(conn: FakeConnection) -> bytes:
    return conn.written.split(b"\r\n", 1)[0]


def test_parse_head():
    head = b"GET /a/b HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\n\r\n"
    assert parse_head(head) == ("GET", "/a/b", {"host": "x", "content-length": "3"})


def test_request_is_parsed_and_passed_to_handler():
    seen: list[Request] = []

    def spy(request: Request) -> IO[Response]:
        seen.append(request)
        return IO.unit(Response(HTTPStatus.OK, ""))

    exchange(b"POST /x HTTP/1.1\r\nContent-Length: 4\r\nX-A: b\r\n\r\nbody", spy)
    assert seen == [Request("POST", "/x", {"content-length": "4", "x-a": "b"}, b"body")]


def test_response_is_encoded():
    conn = exchange(b"GET /hi HTTP/1.1\r\n\r\n", echo_request)
    assert conn.written == (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"Content-Length: 8\r\n"
        b"Connection: close\r\n\r\n"
        b"GET /hi "
    )


@given(st.binary(max_size=200))
def test_body_is_read_by_content_length(body):
    seen: list[bytes] = []

    def spy(request: Request) -> IO[Response]:
        seen.append(request.body)
        return IO.unit(Response(HTTPStatus.OK, ""))

    head = f"POST / HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n".encode()
    conn = exchange(head + body + b"trailing garbage", spy)
    assert seen == [body]
    assert conn.incoming == b"trailing garbage"


def test_content_length_counts_utf8_bytes():
    conn = exchange(
        b"GET / HTTP/1.1\r\n\r\n", lambda _: IO.unit(Response(HTTPStatus.OK, "é"))
    )
    assert b"Content-Length: 2\r\n" in conn.written


@pytest.mark.parametrize(
    "raw",
    [
        b"garbage\r\n\r\n",  # no method/path/version
        b"GET / HTTP/1.1\r\nno-colon\r\n\r\n",  # bad header
        b"GET / HTTP/1.1\r\nContent-Length: nope\r\n\r\n",  # bad length
        b"GET / HTTP/1.1\r\n",  # peer closed before end of head
        b"POST / HTTP/1.1\r\nContent-Length: 10\r\n\r\nshort",  # peer closed before end of body
    ],
)
def test_malformed_request_is_400_and_handler_not_called(raw):
    called: list[Request] = []

    def spy(request: Request) -> IO[Response]:
        called.append(request)
        return IO.unit(Response(HTTPStatus.OK, ""))

    conn = exchange(raw, spy)
    assert status_line(conn) == b"HTTP/1.1 400 Bad Request"
    assert called == []


def test_failing_handler_is_500():
    def boom(_: Request) -> IO[Response]:
        def _raise() -> Response:
            raise RuntimeError("boom")

        return IO(_raise)

    conn = exchange(b"GET / HTTP/1.1\r\n\r\n", boom)
    assert status_line(conn) == b"HTTP/1.1 500 Internal Server Error"
    assert b"RuntimeError('boom')" in conn.written


def test_http_does_not_close_connection():
    """Closing is the tcp layer's job."""
    assert not exchange(b"GET / HTTP/1.1\r\n\r\n", echo_request).closed
