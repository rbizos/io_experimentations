import dataclasses

from monads import IO


@dataclasses.dataclass
class FakeConnection:
    """In-memory Connection: reads consume `incoming`, writes append to `written`."""

    incoming: bytes
    written: bytes = b""
    closed: bool = False
    peer: str = "fake:0"

    def _take(self, n: int) -> bytes:
        if n > len(self.incoming):
            raise EOFError(f"wanted {n} bytes, peer closed after {len(self.incoming)}")
        chunk, self.incoming = self.incoming[:n], self.incoming[n:]
        return chunk

    def read_until(self, separator: bytes) -> IO[bytes]:
        def _read() -> bytes:
            index = self.incoming.find(separator)
            if index < 0:
                raise EOFError(f"peer closed before {separator!r}")
            return self._take(index + len(separator))

        return IO(_read)

    def read_exactly(self, n: int) -> IO[bytes]:
        return IO(lambda: self._take(n))

    def write(self, data: bytes) -> IO[None]:
        def _write() -> None:
            self.written += data

        return IO(_write)

    def close(self) -> IO[None]:
        def _close() -> None:
            self.closed = True

        return IO(_close)
