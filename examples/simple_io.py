import concurrent.futures
import asyncio, threading, time
from monads.io import IO

thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
loop = asyncio.new_event_loop()
loop.set_default_executor(thread_pool)

print(f"Schedule thread: {threading.get_ident()}")
def perform_io_operation_1() -> int:
    # Simulate an expensive operation
    print(f"executing effect 1 in thread: {threading.get_ident()}")
    time.sleep(1)
    return 42


def perform_io_operation_2(data: int) -> IO[str]:
    # Simulate another expensive operation
    print(f"executing effect 2 in thread: {threading.get_ident()}")
    return IO.unit(f"the answer is {data}")


io_1 = IO(perform_io_operation_1).flat_map(perform_io_operation_2)
io_2 = IO.parallel_map([io_1, io_1, io_1, io_1])

print(asyncio.run(io_2.run(), loop_factory=lambda: loop))
