import os
from ..exporters.json_export_visitor import JsonExportVisitor
from ..exporters.yaml_export_visitor import YamlExportVisitor
from ..exporters.csv_export_visitor import CsvExportVisitor
class ExportResolver:
    def resolve(self, fmt_or_path):
        s = (fmt_or_path or '').strip().lower()
        ext = os.path.splitext(s)[1] if '.' in s else ''
        key = ext[1:] if ext else s
        if key in ("yaml", "yml"):
            return YamlExportVisitor()
        if key == "csv":
            return CsvExportVisitor()
        return JsonExportVisitor()