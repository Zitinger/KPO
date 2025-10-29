from abc import ABC, abstractmethod

class IAlive(ABC):
    @property
    @abstractmethod
    def food(self):
        pass
