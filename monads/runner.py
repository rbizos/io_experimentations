import asyncio
from concurrent.futures import ThreadPoolExecutor
from monads.IO_first import IO
import threading
from time import sleep


class SimpleRunner:
    loop: asyncio.AbstractEventLoop
    executor: ThreadPoolExecutor

    async def _run(self, obj):
        while True:
            match obj:
                case IO.unit:
                    return
                case IO(_):
                    obj = obj.run()
                case _:
                    return obj

    def run(self, obj):
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.loop.run_until_complete(self._run(obj))


def printN(i):
    def inner(_=None):
        print(i)
        return IO.unit

    return inner


runner = SimpleRunner()


bonjour = (
    IO.print("bonjour")
    + IO.eval(lambda: sleep(2))
    + IO.eval(lambda: threading.get_native_id())
    >> IO.print
)
main = (
    IO.gather(
        [
            bonjour,
            bonjour,
        ]
    )
    >> IO.print
)
runner.run(main)
