from ..domain.operation_type import OperationType


class AnalyticsFacade:
    def __init__(self, acc_repo, cat_repo, op_repo):
        self._acc_repo = acc_repo
        self._cat_repo = cat_repo
        self._op_repo = op_repo

    def income_expense_diff(self, date_from=None, date_to=None):
        income = 0.0
        expense = 0.0
        for x in self._op_repo.all():
            if date_from and x.date < date_from:
                continue
            if date_to and x.date > date_to:
                continue
            if x.type == OperationType.INCOME:
                income += x.amount
            else:
                expense += x.amount
        return income - expense

    def group_by_category(self):
        res = {}
        for x in self._op_repo.all():
            k = x.category_id or "unknown"
            res.setdefault(k, 0.0)
            if x.type == OperationType.INCOME:
                res[k] += x.amount
            else:
                res[k] -= x.amount
        return res
