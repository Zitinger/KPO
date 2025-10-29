from abc import ABC, abstractmethod

class IInventory(ABC):
    @property
    @abstractmethod
    def number(self):
        pass

    @number.setter
    @abstractmethod
    def number(self, value):
        pass
