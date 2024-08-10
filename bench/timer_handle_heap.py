from asyncio import TimerHandle
import heapq
import timeit


def callback():
    """This is the callback function that will be called when the timer expires."""


class MockLoop:
    def get_debug(self):
        return False


loop = MockLoop()


def heap_tuple():
    scheduled = []
    when = 1

    for _ in range(100):
        when += 1
        handle = TimerHandle(when, callback, (), loop)
        heapq.heappush(scheduled, (when, handle))

    while scheduled:
        when, handle = heapq.heappop(scheduled)


def heap_handle():
    scheduled = []
    when = 1

    for _ in range(100):
        when += 1
        handle = TimerHandle(when, callback, (), loop)
        heapq.heappush(scheduled, handle)

    while scheduled:
        handle = heapq.heappop(scheduled)


print("wrap when, TimerHandle in tuple", timeit.timeit(heap_tuple))
print("bare TimerHandle", timeit.timeit(heap_handle))
