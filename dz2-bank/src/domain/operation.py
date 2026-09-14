class Operation:
    def __init__(self, id, type, bank_account_id, amount, date, description, category_id):
        self.id = id
        self.type = type
        self.bank_account_id = bank_account_id
        self.amount = amount
        self.date = date
        self.description = description
        self.category_id = category_id
