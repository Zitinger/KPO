from ..factory.entity_factory import EntityFactory


class CategoryFacade:
    def __init__(self, repo):
        self._repo = repo
        self._factory = EntityFactory()

    def create(self, type, name):
        cat = self._factory.category(type, name)
        self._repo.add(cat)
        return cat

    def list(self):
        return self._repo.all()

    def update(self, id, name=None, type=None):
        cat = self._repo.get(id)
        if cat is None:
            return None
        if name is not None:
            cat.name = name
        if type is not None:
            cat.type = type
        self._repo.update(cat)
        return cat

    def delete(self, id):
        self._repo.delete(id)
