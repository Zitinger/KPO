from abc import ABC, abstractmethod
from ..factory.entity_factory import EntityFactory


class BaseImporter(ABC):
    def __init__(self):
        self.factory = EntityFactory()

    def import_file(self, path, acc_repo, cat_repo, op_repo):
        raw = self._read(path)
        data = self._parse(raw) or {}
        acc_map = {}
        for a in data.get("accounts", []):
            name = a.get("name", "")
            bal = a.get("balance", 0.0)
            old_id = a.get("id")
            acc = self.factory.bank_account(name, bal)
            acc_repo.add(acc)
            if old_id:
                acc_map[old_id] = acc.id
        cat_map = {}
        for c in data.get("categories", []):
            old_id = c.get("id")
            obj = self.factory.category(c["type"], c["name"])
            cat_repo.add(obj)
            if old_id:
                cat_map[old_id] = obj.id
        for o in data.get("operations", []):
            t = o["type"]
            ba = o.get("bank_account_id")
            if ba in acc_map:
                ba = acc_map[ba]
            ca = o.get("category_id")
            if ca in cat_map:
                ca = cat_map[ca]
            amount = o["amount"]
            date = o["date"]
            desc = o.get("description")
            op = self.factory.operation(t, ba, amount, date, desc, ca)
            op_repo.add(op)

    @abstractmethod
    def _read(self, path):
        ...

    @abstractmethod
    def _parse(self, content):
        ...
