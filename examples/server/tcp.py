"""
TCP layer: a server is an IO that, per connection, runs a `Connection -> IO[None]` handler.

The handler gets reads and writes as IO values and knows nothing about asyncio;
the connection is always closed after the handler finishes, and a failing handler
is reported without killing the server.

    python -m examples.server.tcp       # line-based upper-casing echo server
    nc localhost 8081
"""

import asyncio
import dataclasses
from collections.abc import Callable
from typing import Protocol

from monads import IO, Err, Ok, Result


class Connection(Protocol):
    """What a handler can do with a connection; implemented over sockets by StreamConnection."""

    @property
    def peer(self) -> str: ...

    def read_until(self, separator: bytes) -> IO[bytes]:
        """Fails if the peer closes before `separator`."""
        ...

    def read_exactly(self, n: int) -> IO[bytes]:
        """Fails if the peer closes before `n` bytes."""
        ...

    def write(self, data: bytes) -> IO[None]: ...

    def close(self) -> IO[None]: ...


@dataclasses.dataclass(frozen=True)
class StreamConnection:
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter

    @property
    def peer(self) -> str:
        host, port, *_ = self._writer.get_extra_info("peername")
        return f"{host}:{port}"

    def read_until(self, separator: bytes) -> IO[bytes]:
        return IO.from_async(lambda: self._reader.readuntil(separator))

    def read_exactly(self, n: int) -> IO[bytes]:
        return IO.from_async(lambda: self._reader.readexactly(n))

    def write(self, data: bytes) -> IO[None]:
        async def _write() -> None:
            self._writer.write(data)
            await self._writer.drain()

        return IO.from_async(_write)

    def close(self) -> IO[None]:
        async def _close() -> None:
            self._writer.close()
            await self._writer.wait_closed()

        return IO.from_async(_close)


type ConnectionHandler = Callable[[Connection], IO[None]]


def serve(host: str, port: int, handler: ConnectionHandler) -> IO[None]:
    def _session(conn: Connection) -> IO[None]:
        # attempt() so that close always runs, then report the failure if any
        return handler(conn).attempt().flat_map(
            lambda result: conn.close().flat_map(lambda _: _report(conn, result))
        )

    async def _on_connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await _session(StreamConnection(reader, writer)).run_async()

    async def _serve() -> None:
        server = await asyncio.start_server(_on_connect, host, port)
        print(f"listening on {host}:{port}")
        async with server:
            await server.serve_forever()

    return IO.from_async(_serve)


def _report(conn: Connection, result: Result[None, Exception]) -> IO[None]:
    match result:
        case Err(e):
            return IO.print(f"connection {conn.peer} failed: {e!r}")
        case Ok(_):
            return IO.unit(None)


def lines(handler: Callable[[str], IO[str]]) -> ConnectionHandler:
    """
    Line protocol: each received line is answered with handler(line), until the peer disconnects.

    The loop is a plain `while` rather than recursive flat_map: IO binds nest awaits,
    so a recursive loop would overflow the stack on long sessions.
    """

    def _on_connection(conn: Connection) -> IO[None]:
        async def _loop() -> None:
            while True:
                received = await conn.read_until(b"\n").attempt().run_async()
                match received:
                    case Ok(line):
                        reply = await handler(line.decode().rstrip("\r\n")).run_async()
                        await conn.write(f"{reply}\n".encode()).run_async()
                    case Err(_):  # peer closed
                        return

        return IO.from_async(_loop)

    return _on_connection


if __name__ == "__main__":
    serve("127.0.0.1", 8081, lines(lambda line: IO.unit(line.upper()))).run()
