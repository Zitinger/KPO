class Container:
    def __init__(self):
        self._instances = {}

    def register_instance(self, key, instance):
        self._instances[key] = instance

    def resolve(self, key):
        return self._instances[key]
