from ..factory.entity_factory import EntityFactory
from ..domain.operation_type import OperationType
from ..builders.operation_builder import OperationBuilder


class OperationFacade:
    def __init__(self, repo):
        self._repo = repo
        self._factory = EntityFactory()

    def builder(self):
        return OperationBuilder(self._factory)

    def add_op(self, op):
        self._repo.add(op)
        return op

    def create(self, type, bank_account_id, amount, date, description, category_id):
        op = self._factory.operation(type, bank_account_id, amount, date, description, category_id)
        self._repo.add(op)
        return op

    def list(self):
        return self._repo.all()

    def update(self, id, **kwargs):
        op = self._repo.get(id)
        if op is None:
            return None
        for k, v in kwargs.items():
            if hasattr(op, k) and v is not None:
                setattr(op, k, v)
        self._repo.update(op)
        return op

    def delete(self, id):
        self._repo.delete(id)

    def recalc_balance(self, accounts_repo):
        for acc in accounts_repo.all():
            acc.balance = 0.0
            accounts_repo.update(acc)
        for op in self._repo.all():
            acc = accounts_repo.get(op.bank_account_id)
            if acc:
                if op.type == OperationType.INCOME:
                    acc.balance += op.amount
                else:
                    acc.balance -= op.amount
                accounts_repo.update(acc)
