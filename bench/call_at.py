import asyncio
import timeit


def run():
    asyncio.run(call_at())


async def call_at():
    loop = asyncio.get_running_loop()
    when = loop.time()
    future = loop.create_future()

    def callback():
        """Callback function."""

    def done():
        """Done function."""
        future.set_result(None)

    for _ in range(100):
        when += 0.00000001
        loop.call_at(when, callback)

    loop.call_at(when, done)
    await future


print("call_at_benchmark", timeit.timeit(run))
