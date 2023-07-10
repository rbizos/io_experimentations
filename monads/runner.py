import asyncio
from monads.IO import IO


class SimpleRunner:
    loop: asyncio.AbstractEventLoop

    async def _run(self, obj):
        while True:
            # print(obj)
            match obj:
                case IO.unit:
                    return
                case IO():
                    obj = await self.loop.run_in_executor(None, obj._effect)
                case _ if isinstance(obj, tuple):
                    return await asyncio.gather(*[self._run(member) for member in obj])
                case _:
                    return obj

    def run(self, obj):
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._run(obj))


runner = SimpleRunner()

hello_world = IO.print("hello") & IO.print("world")
hello_who = IO.input("hello who ?").map(lambda x: f"hello {x}") >> IO.print

main = hello_who & hello_who


runner.run(main)
