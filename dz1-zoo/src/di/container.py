class Container:
    def __init__(self):
        self._factories = {}
        self._singletons = {}

    def register(self, key, factory):
        self._factories[key] = factory

    def resolve(self, key):
        if key not in self._singletons:
            self._singletons[key] = self._factories[key](self)
        return self._singletons[key]
