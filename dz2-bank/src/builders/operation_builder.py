class OperationBuilder:
    def __init__(self, factory):
        self.factory = factory
        self._type = None
        self._bank_account_id = None
        self._amount = None
        self._date = None
        self._description = None
        self._category_id = None

    def with_type(self, t):
        self._type = t
        return self

    def with_account(self, acc_id):
        self._bank_account_id = acc_id
        return self

    def with_amount(self, amount):
        self._amount = amount
        return self

    def with_date(self, date):
        self._date = date
        return self

    def with_description(self, desc):
        self._description = desc
        return self

    def with_category(self, cat_id):
        self._category_id = cat_id
        return self

    def build(self):
        return self.factory.operation(self._type, self._bank_account_id, self._amount, self._date, self._description,
                                      self._category_id)
