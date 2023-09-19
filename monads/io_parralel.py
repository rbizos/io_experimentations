
import asyncio
from typing import TypeVar, Generic, Callable, List, Any
import concurrent.futures
import threading
T = TypeVar('T')

class IO(Generic[T]):
    def __init__(self, func: Callable[[], T]):
        self.func = func

    def run(self) -> T:
        return self.func()

    def map(self, func: Callable[[T], Any]) -> 'IO':
        def new_func() -> Any:
            result = self.run()
            return func(result)
        return IO(new_func)

    def flat_map(self, func: Callable[[T], 'IO']) -> 'IO':
        def new_func() -> T:
            result_io = self.run()
            return func(result_io.run()).run()
        return IO(new_func)



    @staticmethod
    def parallel_map(io_list: List['IO[T]'], thread_pool: concurrent.futures.ThreadPoolExecutor) -> 'IO[List[T]]':
        async def parallel_map_async():
            print(f"scheduling: {threading.get_ident()}")
            loop = asyncio.get_event_loop()

            results = await asyncio.gather(*[loop.run_in_executor(thread_pool, io.run,) for io in io_list])
            return results

        return IO(lambda: asyncio.run(parallel_map_async()))


    @classmethod
    def pure(cls, value: T) -> 'IO[T]':
        return cls(lambda: value)

import concurrent.futures

# Create a ThreadPoolExecutor with a specific number of threads
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
print(f"main: {threading.get_ident()}")
a = 0
def perform_io_operation_1() -> int:
    # Simulate an expensive operation
    print(f"executing effect: {threading.get_ident()}")
    return 42

def perform_io_operation_2(data: int) -> str:
    # Simulate another expensive operation
    print(f"executing effect: {threading.get_ident()}")
    return f"Result: {data}"

io_1 = IO(perform_io_operation_1)
io_2 = io_1.map(perform_io_operation_2)


# You can reuse the same thread pool for other parallel mapping operations
io_3 = IO.parallel_map([io_1.map(perform_io_operation_2)], thread_pool=thread_pool)
print(io_3.run())
result3 = IO.parallel_map([io_3, io_3], thread_pool=thread_pool)
print(result3.run())  # Output: ['Result: 42']

