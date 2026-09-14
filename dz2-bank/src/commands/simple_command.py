from .command import Command


class SimpleCommand(Command):
    def __init__(self, func):
        self._func = func

    def execute(self):
        return self._func()
