"""
HTTP/1.1 layer on top of tcp: turns a `Request -> IO[Response]` handler into a ConnectionHandler.

One request per connection (Connection: close). A malformed request is answered with 400,
a failing handler with 500; both via IO.attempt, no try/except.
"""

import dataclasses
from collections.abc import Callable
from http import HTTPStatus

from monads import IO, Err, Ok, Result

from .tcp import Connection, ConnectionHandler


@dataclasses.dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@dataclasses.dataclass(frozen=True)
class Response:
    status: HTTPStatus
    body: str
    content_type: str = "text/plain; charset=utf-8"

    def encode(self) -> bytes:
        payload = self.body.encode()
        head = (
            f"HTTP/1.1 {self.status.value} {self.status.phrase}\r\n"
            f"Content-Type: {self.content_type}\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Connection: close\r\n\r\n"
        )
        return head.encode() + payload


type Handler = Callable[[Request], IO[Response]]


def parse_head(head: bytes) -> tuple[str, str, dict[str, str]]:
    """Pure; raises ValueError on malformed input."""
    request_line, *header_lines = head.decode("latin-1").rstrip("\r\n").split("\r\n")
    method, path, _version = request_line.split(" ", 2)
    headers = {k.strip().lower(): v.strip() for k, v in (h.split(":", 1) for h in header_lines)}
    return method, path, headers


def read_request(conn: Connection) -> IO[Request]:
    def _with_body(head: bytes) -> IO[Request]:
        method, path, headers = parse_head(head)
        return conn.read_exactly(int(headers.get("content-length", "0"))).map(
            lambda body: Request(method, path, headers, body)
        )

    return conn.read_until(b"\r\n\r\n").flat_map(_with_body)


def _error(status: HTTPStatus, e: Exception) -> Response:
    return Response(status, f"{status.phrase}: {e!r}\n")


def _or_error(status: HTTPStatus) -> Callable[[Result[Response, Exception]], Response]:
    def _fold(result: Result[Response, Exception]) -> Response:
        match result:
            case Ok(response):
                return response
            case Err(e):
                return _error(status, e)

    return _fold


def _respond(handler: Handler, request: Result[Request, Exception]) -> IO[Response]:
    match request:
        case Ok(req):
            return handler(req).attempt().map(_or_error(HTTPStatus.INTERNAL_SERVER_ERROR))
        case Err(e):
            return IO.unit(_error(HTTPStatus.BAD_REQUEST, e))


def http(handler: Handler) -> ConnectionHandler:
    return lambda conn: (
        read_request(conn)
        .attempt()
        .flat_map(lambda request: _respond(handler, request))
        .flat_map(lambda response: conn.write(response.encode()))
    )
