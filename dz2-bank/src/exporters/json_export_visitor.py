import json
from .export_visitor import ExportVisitor


class JsonExportVisitor(ExportVisitor):
    def visit_exportable_data(self, data, path):
        payload = {
            "accounts": data.accounts,
            "categories": data.categories,
            "operations": data.operations,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
