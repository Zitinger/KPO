from ..ids.id_generator import IdGenerator
from ..domain.bank_account import BankAccount
from ..domain.category import Category
from ..domain.operation import Operation
from ..domain.operation_type import OperationType


class EntityFactory:
    def __init__(self, id_generator=None):
        self._ids = id_generator or IdGenerator()

    def bank_account(self, name, balance=0.0):
        if balance < 0:
            raise ValueError("balance")
        return BankAccount(self._ids.new_id(), name, float(balance))

    def category(self, type, name):
        from ..domain.category_type import CategoryType
        if isinstance(type, str):
            type = CategoryType(type)
        return Category(self._ids.new_id(), type, name)

    def operation(self, type, bank_account_id, amount, date, description, category_id):
        if amount <= 0:
            raise ValueError("amount")
        if isinstance(type, str):
            type = OperationType(type)
        if type not in (OperationType.INCOME, OperationType.EXPENSE):
            raise ValueError("type")
        return Operation(self._ids.new_id(), type, bank_account_id, float(amount), date, description, category_id)
