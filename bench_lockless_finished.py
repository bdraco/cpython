#!/usr/bin/env python3
"""Benchmark the lockless optimization for finished futures."""

import concurrent.futures
import time
import statistics
import threading


# Original implementation (always locks)
def _get_snapshot_with_lock(self):
    """Always uses lock."""
    with self._condition:
        if self._state == "FINISHED":
            return True, False, self._result, self._exception
        if self._state in {"CANCELLED", "CANCELLED_AND_NOTIFIED"}:
            return True, True, None, None
        return False, False, None, None


# Optimized implementation (skips lock for finished)
def _get_snapshot_lockless_finished(self):
    """Skips lock for finished futures."""
    # Fast path: check if already finished without lock
    if self._state == "FINISHED":
        return True, False, self._result, self._exception

    # Need lock for other states since they can change
    with self._condition:
        if self._state == "FINISHED":
            return True, False, self._result, self._exception
        if self._state in {"CANCELLED", "CANCELLED_AND_NOTIFIED"}:
            return True, True, None, None
        return False, False, None, None


def benchmark_function(func, iterations=100000, warmup=1000):
    """Run a benchmark on a function and return mean in nanoseconds."""
    # Warmup
    for _ in range(warmup):
        func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1e9)

    return statistics.mean(times), statistics.stdev(times)


def run_benchmarks():
    """Compare performance of both implementations."""
    print("=== Lockless Optimization for Finished Futures ===\n")

    # Test with a finished future (most common case)
    future = concurrent.futures.Future()
    future.set_result(42)

    # Test original implementation
    concurrent.futures.Future._get_snapshot = _get_snapshot_with_lock

    def test_with_lock():
        return future._get_snapshot()

    with_lock_time, with_lock_std = benchmark_function(test_with_lock)

    # Test optimized implementation
    concurrent.futures.Future._get_snapshot = _get_snapshot_lockless_finished

    def test_lockless():
        return future._get_snapshot()

    lockless_time, lockless_std = benchmark_function(test_lockless)

    print(f"Finished future (most common case):")
    print(f"With lock:    {with_lock_time:8.2f} ns ± {with_lock_std:6.2f} ns")
    print(f"Lockless:     {lockless_time:8.2f} ns ± {lockless_std:6.2f} ns")
    print(f"Speedup:      {with_lock_time / lockless_time:8.2f}x\n")

    # Test with different states
    states = {
        "finished": lambda f: f.set_result(100),
        "exception": lambda f: f.set_exception(ValueError("test")),
        "cancelled": lambda f: f.cancel(),
        "pending": lambda f: None,  # Don't set any state
    }

    print("Comparison across different states:")
    print(f"{'State':10} {'With Lock':>12} {'Lockless':>12} {'Speedup':>10}")
    print("-" * 50)

    for state_name, setup_func in states.items():
        # Create future in the desired state
        test_future = concurrent.futures.Future()
        setup_func(test_future)

        # Test with lock
        concurrent.futures.Future._get_snapshot = _get_snapshot_with_lock

        def test_state_with_lock():
            return test_future._get_snapshot()

        time_with_lock, _ = benchmark_function(test_state_with_lock)

        # Test lockless
        concurrent.futures.Future._get_snapshot = (
            _get_snapshot_lockless_finished
        )

        def test_state_lockless():
            return test_future._get_snapshot()

        time_lockless, _ = benchmark_function(test_state_lockless)

        speedup = (
            time_with_lock / time_lockless
            if time_lockless > 0
            else float("inf")
        )
        print(
            f"{state_name:10} {time_with_lock:10.2f} ns {time_lockless:10.2f} ns {speedup:8.2f}x"
        )

    # Test concurrent access scenario
    print("\nConcurrent access test (high contention):")

    future = concurrent.futures.Future()
    future.set_result(42)

    def concurrent_test(impl_func, iterations=10000):
        concurrent.futures.Future._get_snapshot = impl_func

        def worker():
            for _ in range(iterations):
                future._get_snapshot()

        threads = []
        start = time.perf_counter()

        for _ in range(4):  # 4 threads
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        end = time.perf_counter()
        return (end - start) * 1e9 / (4 * iterations)  # ns per call

    with_lock_concurrent = concurrent_test(_get_snapshot_with_lock)
    lockless_concurrent = concurrent_test(_get_snapshot_lockless_finished)

    print(f"With lock:    {with_lock_concurrent:8.2f} ns/call")
    print(f"Lockless:     {lockless_concurrent:8.2f} ns/call")
    print(f"Speedup:      {with_lock_concurrent / lockless_concurrent:8.2f}x")


if __name__ == "__main__":
    run_benchmarks()
