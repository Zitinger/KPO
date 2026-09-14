import yaml
from .export_visitor import ExportVisitor


class YamlExportVisitor(ExportVisitor):
    def visit_exportable_data(self, data, path):
        payload = {
            "accounts": data.accounts,
            "categories": data.categories,
            "operations": data.operations,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
        return path
