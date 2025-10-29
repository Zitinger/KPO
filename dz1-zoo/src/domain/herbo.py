from .animal import Animal

class Herbo(Animal):
    def __init__(self, name, food, kindness=0):
        super().__init__(name, food)
        if not (0 <= kindness <= 10):
            raise ValueError("Доброта должна быть в диапазоне [0, 10]")
        self.kindness = kindness

    def is_petting_candidate(self):
        return self.kindness > 5
