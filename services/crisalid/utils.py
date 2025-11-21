import contextlib
import time


@contextlib.contextmanager
def timeit(to_log, prefix=""):
    """ContextManager to mesure time of runing function"""
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        to_log(f"{prefix}total time: {end  - start:.2f}s")
