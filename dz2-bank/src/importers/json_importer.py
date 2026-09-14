import json
from .base_importer import BaseImporter


class JsonImporter(BaseImporter):
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse(self, content):
        return json.loads(content)
