import yaml
from .base_importer import BaseImporter


class YamlImporter(BaseImporter):
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse(self, content):
        return yaml.safe_load(content) or {}
