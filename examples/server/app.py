"""
Application on top of the http layer: routes are pure `Request -> IO[Response]` functions.

    python -m examples.server.app
    curl localhost:8080/hello/bob
    curl localhost:8080/count
    curl -d 'ping' localhost:8080/echo
    curl localhost:8080/slow        # two 1s effects run in parallel with `&`: ~1s total
    curl localhost:8080/boom        # failing handler -> 500
"""

import threading
import time
from collections.abc import Callable
from http import HTTPStatus

from monads import IO

from .http import Handler, Request, Response, http
from .tcp import serve


def ok(body: str) -> IO[Response]:
    return IO.unit(Response(HTTPStatus.OK, body))


def not_found(request: Request) -> IO[Response]:
    return IO.unit(Response(HTTPStatus.NOT_FOUND, f"no route for {request.method} {request.path}\n"))


def sleep(seconds: float, value: str) -> IO[str]:
    return IO(lambda: (time.sleep(seconds), value)[1])


def fail(message: str) -> IO[Response]:
    def _raise() -> Response:
        raise RuntimeError(message)

    return IO(_raise)


def make_counter() -> Callable[[], IO[int]]:
    """The mutable cell lives outside IO; reading+incrementing it is the effect."""
    lock, cell = threading.Lock(), [0]

    def _incr() -> int:
        with lock:
            cell[0] += 1
            return cell[0]

    return lambda: IO(_incr)


def router(count: Callable[[], IO[int]]) -> Handler:
    def route(request: Request) -> IO[Response]:
        match request.method, request.path.strip("/").split("/"):
            case "GET", [""]:
                return ok("hello from IO\n")
            case "GET", ["hello", name]:
                return ok(f"hello {name}\n")
            case "GET", ["count"]:
                return count().map(lambda n: Response(HTTPStatus.OK, f"{n}\n"))
            case "POST", ["echo"]:
                return ok(request.body.decode())
            case "GET", ["slow"]:
                return (sleep(1, "a") & sleep(1, "b")).map(
                    lambda ab: Response(HTTPStatus.OK, f"{ab[0]}{ab[1]}\n")
                )
            case "GET", ["boom"]:
                return fail("boom")
            case _:
                return not_found(request)

    return route


def logged(handler: Handler) -> Handler:
    """Middleware is just Handler -> Handler."""

    def _log(request: Request) -> IO[Request]:
        return IO.print(f"[thread {threading.get_ident()}] {request.method} {request.path}").map(
            lambda _: request
        )

    return lambda request: _log(request) >> handler


main = serve("127.0.0.1", 8080, http(logged(router(make_counter()))))

if __name__ == "__main__":
    main.run()
