from hypothesis import given, strategies as st

from examples.server.tcp import lines
from monads import IO

from .fake_connection import FakeConnection

line_texts = st.lists(st.text(alphabet=st.characters(exclude_characters="\r\n")), max_size=20)


@given(line_texts)
def test_lines_answers_each_line_in_order(texts):
    conn = FakeConnection("".join(f"{t}\n" for t in texts).encode())
    lines(lambda line: IO.unit(line.upper()))(conn).run()
    assert conn.written == "".join(f"{t.upper()}\n" for t in texts).encode()


def test_lines_strips_crlf():
    conn = FakeConnection(b"a\r\nb\n")
    lines(lambda line: IO.unit(f"<{line}>"))(conn).run()
    assert conn.written == b"<a>\n<b>\n"


def test_lines_stops_on_partial_line():
    conn = FakeConnection(b"a\nincomplete")
    lines(IO.unit)(conn).run()
    assert conn.written == b"a\n"


def test_lines_is_stack_safe():
    n = 5_000
    conn = FakeConnection(b"x\n" * n)
    lines(IO.unit)(conn).run()
    assert conn.written == b"x\n" * n
