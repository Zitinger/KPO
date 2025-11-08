from .repository import Repository
from ..domain.category import Category
from ..domain.category_type import CategoryType
from ..domain.operation import Operation
from ..domain.operation_type import OperationType
from ..domain.bank_account import BankAccount


class FileBackedRepositoryProxy(Repository):
    def __init__(self, inner_repo, storage):
        self._inner = inner_repo
        self._storage = storage
        for item in self._storage.load():
            self._load_item(item)

    def _load_item(self, item):
        if "balance" in item and "name" in item:
            obj = BankAccount(item["id"], item["name"], item["balance"])
        elif "bank_account_id" in item:
            t = OperationType(item["type"])
            obj = Operation(item["id"], t, item["bank_account_id"], item["amount"], item["date"],
                            item.get("description"), item.get("category_id"))
        else:
            t = CategoryType(item["type"])
            obj = Category(item["id"], t, item["name"])
        self._inner.add(obj)

    def _flush(self):
        self._storage.save(self._inner.snapshot())

    def add(self, obj):
        self._inner.add(obj)
        self._flush()

    def get(self, id):
        return self._inner.get(id)

    def update(self, obj):
        self._inner.update(obj)
        self._flush()

    def delete(self, id):
        self._inner.delete(id)
        self._flush()

    def all(self):
        return self._inner.all()

    def snapshot(self):
        return self._inner.snapshot()
