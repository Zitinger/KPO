class ExportableData:
    def __init__(self, accounts, categories, operations):
        self.accounts = accounts
        self.categories = categories
        self.operations = operations

    def accept(self, visitor, path):
        return visitor.visit_exportable_data(self, path)
