import io
from .base_importer import BaseImporter


class CsvImporter(BaseImporter):
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse(self, content):
        sections = {"accounts": [], "categories": [], "operations": []}
        current = None
        header = None
        for raw in io.StringIO(content):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#accounts"):
                current = "accounts";
                header = None;
                continue
            if line.startswith("#categories"):
                current = "categories";
                header = None;
                continue
            if line.startswith("#operations"):
                current = "operations";
                header = None;
                continue
            if current is None:
                continue
            if header is None:
                header = [x.strip() for x in line.split(",")]
                continue
            values = [x.strip() for x in line.split(",")]
            row = {h: v for h, v in zip(header, values)}
            if current == "accounts" and "balance" in row and row["balance"] != "":
                try:
                    row["balance"] = float(row["balance"])
                except:
                    pass
            if current == "operations" and "amount" in row and row["amount"] != "":
                try:
                    row["amount"] = float(row["amount"])
                except:
                    pass
            sections[current].append(row)
        return sections
