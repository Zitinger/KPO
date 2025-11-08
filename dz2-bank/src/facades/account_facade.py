from ..factory.entity_factory import EntityFactory


class AccountFacade:
    def __init__(self, repo):
        self._repo = repo
        self._factory = EntityFactory()

    def create(self, name, balance=0.0):
        acc = self._factory.bank_account(name, balance)
        self._repo.add(acc)
        return acc

    def list(self):
        return self._repo.all()

    def update(self, id, name=None, balance=None):
        acc = self._repo.get(id)
        if acc is None:
            return None
        if name is not None:
            acc.name = name
        if balance is not None:
            if balance < 0:
                raise ValueError("balance")
            acc.balance = float(balance)
        self._repo.update(acc)
        return acc

    def delete(self, id):
        self._repo.delete(id)
