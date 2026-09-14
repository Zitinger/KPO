from .repository import Repository


class InMemoryCategoryRepository(Repository):
    def __init__(self):
        self._data = {}

    def add(self, obj):
        self._data[obj.id] = obj

    def get(self, id):
        return self._data.get(id)

    def update(self, obj):
        self._data[obj.id] = obj

    def delete(self, id):
        self._data.pop(id, None)

    def all(self):
        return list(self._data.values())

    def snapshot(self):
        return [{"id": x.id, "type": x.type.value, "name": x.name} for x in self.all()]
