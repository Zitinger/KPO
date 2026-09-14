import csv, os
from .export_visitor import ExportVisitor


class CsvExportVisitor(ExportVisitor):
    def visit_exportable_data(self, data, path):
        base = os.path.splitext(path)[0]
        a = base + "_accounts.csv"
        c = base + "_categories.csv"
        o = base + "_operations.csv"
        with open(a, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "name", "balance"])
            w.writeheader()
            for x in data.accounts:
                w.writerow(x)
        with open(c, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "type", "name"])
            w.writeheader()
            for x in data.categories:
                w.writerow(x)
        with open(o, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "type", "bank_account_id", "amount", "date", "description",
                                              "category_id"])
            w.writeheader()
            for x in data.operations:
                w.writerow(x)
        return base
