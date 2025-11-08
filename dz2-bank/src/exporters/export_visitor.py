from abc import ABC, abstractmethod


class ExportVisitor(ABC):
    @abstractmethod
    def visit_exportable_data(self, data, path): ...
