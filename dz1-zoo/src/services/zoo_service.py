from domain.animal import Animal
from domain.herbo import Herbo
from domain.thing import Thing
from domain.i_health_policy import IHealthPolicy
from .inventory_registry import InventoryRegistry

class ZooService:
    def __init__(self, health_policy: IHealthPolicy, inventory: InventoryRegistry):
        self.health_policy = health_policy
        self.inventory = inventory
        self.animals = []
        self.things = []

    def admit_animal(self, animal: Animal):
        if self.health_policy.is_healthy(animal):
            self.inventory.register(animal)
            self.animals.append(animal)
            return True
        return False

    def add_thing(self, thing: Thing):
        num = self.inventory.register(thing)
        self.things.append(thing)
        return num

    def total_food_per_day(self):
        s = 0
        for a in self.animals:
            s += a.food
        return s

    def petting_candidates(self):
        res = []
        for a in self.animals:
            if isinstance(a, Herbo) and a.is_petting_candidate():
                res.append(a)
        return res

    def inventory_report(self):
        return self.inventory.list_items()
