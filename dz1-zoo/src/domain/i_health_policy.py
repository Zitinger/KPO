from abc import ABC, abstractmethod

class IHealthPolicy(ABC):
    @abstractmethod
    def is_healthy(self, animal):
        pass
