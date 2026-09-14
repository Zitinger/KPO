import time
from .command import Command


class TimingDecorator(Command):
    def __init__(self, inner, on_done=None):
        self._inner = inner
        self._on_done = on_done

    def execute(self):
        t0 = time.perf_counter()
        result = self._inner.execute()
        dt = time.perf_counter() - t0
        if self._on_done:
            self._on_done(self._inner.__class__.__name__, dt)
        return result
