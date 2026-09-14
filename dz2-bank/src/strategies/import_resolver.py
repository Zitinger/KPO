import os
from ..importers.json_importer import JsonImporter
from ..importers.yaml_importer import YamlImporter
from ..importers.csv_importer import CsvImporter
class ImportResolver:
    def resolve(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".yaml", ".yml"):
            return YamlImporter()
        if ext == ".csv":
            return CsvImporter()
        return JsonImporter()