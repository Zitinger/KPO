from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def add(self, obj): ...

    @abstractmethod
    def get(self, id): ...

    @abstractmethod
    def update(self, obj): ...

    @abstractmethod
    def delete(self, id): ...

    @abstractmethod
    def all(self): ...

    @abstractmethod
    def snapshot(self): ...
