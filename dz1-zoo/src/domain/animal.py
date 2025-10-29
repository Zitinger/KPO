from .i_alive import IAlive
from .i_inventory import IInventory

class Animal(IAlive, IInventory):
    def __init__(self, name, food):
        if not name:
            raise ValueError("Имя не может быть пустым")
        if food < 0:
            raise ValueError("Расход еды (кг/сутки) должен быть неотрицательным")
        self._name = name
        self._food = food
        self._number = 0

    @property
    def name(self):
        return self._name

    @property
    def food(self):
        return self._food

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, value):
        if value <= 0:
            raise ValueError("Инвентарный номер должен быть положительным")
        if self._number != 0:
            raise ValueError("Инвентарный номер уже присвоен")
        self._number = value

    def display_name(self):
        return f"{self.__class__.__name__} {self._name}"
