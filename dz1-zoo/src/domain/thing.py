from .i_inventory import IInventory

class Thing(IInventory):
    def __init__(self, title):
        if not title:
            raise ValueError("Название предмета не может быть пустым")
        self._title = title
        self._number = 0

    @property
    def title(self):
        return self._title

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
        return f"{self.__class__.__name__} {self._title}"
