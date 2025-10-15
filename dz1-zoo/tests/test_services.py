from services.inventory_registry import InventoryRegistry
from services.zoo_service import ZooService
from domain.thing import Thing
from domain.herbo import Herbo
from domain.predator import Predator
import pytest
from services.random_health_policy import RandomHealthPolicy

def test_inventory_numbers_increase_and_list():
    inv = InventoryRegistry(start_from=100)
    t = Thing(title="Компьютер")
    n1 = inv.register(t)
    a = Predator(name="Лев", food=8)
    n2 = inv.register(a)
    assert n1 == 100
    assert n2 == 101
    items = inv.list_items()
    assert items[0][0] == 100
    assert items[1][0] == 101

def test_zoo_admit_and_totals_accept_all():
    policy = RandomHealthPolicy(healthy_prob=1.0)
    zoo = ZooService(policy, InventoryRegistry(start_from=1))
    a1 = Herbo(name="Олень", food=3, kindness=7)
    a2 = Predator(name="Рысь", food=5)
    ok1 = zoo.admit_animal(a1)
    ok2 = zoo.admit_animal(a2)
    assert ok1 is True
    assert ok2 is True
    assert a1.number == 1
    assert a2.number == 2
    assert zoo.total_food_per_day() == 8

def test_zoo_petting_candidates_and_report():
    policy = RandomHealthPolicy(healthy_prob=1.0)
    zoo = ZooService(policy, InventoryRegistry(start_from=10))
    a1 = Herbo(name="Кролик", food=1, kindness=6)
    a2 = Herbo(name="Коза", food=2, kindness=5)
    zoo.admit_animal(a1)
    zoo.admit_animal(a2)
    cands = zoo.petting_candidates()
    assert len(cands) == 1
    assert cands[0].name == "Кролик"
    rep = zoo.inventory_report()
    assert rep[0][0] == 10
    assert rep[1][0] == 11

def test_zoo_reject_all():
    policy = RandomHealthPolicy(healthy_prob=0.0)
    zoo = ZooService(policy, InventoryRegistry(start_from=1))
    a = Predator(name="Волк", food=4)
    ok = zoo.admit_animal(a)
    assert ok is False
    assert len(zoo.animals) == 0

def test_random_policy_per_animal_rng():
    p = RandomHealthPolicy(healthy_prob=0.5)
    a1 = Predator(name="Лиса", food=1)
    a2 = Predator(name="Ягуар", food=2)
    r1_first = p.is_healthy(a1)
    r1_second = p.is_healthy(a1)
    r2_first = p.is_healthy(a2)
    assert isinstance(r1_first, bool)
    assert isinstance(r1_second, bool)
    assert isinstance(r2_first, bool)
    assert p._rngs.get(a1) is not None
    assert p._rngs.get(a2) is not None
    assert p._rngs[a1] is not p._rngs[a2]

def test_random_policy_prob_validation():
    with pytest.raises(ValueError):
        RandomHealthPolicy(-0.1)
    with pytest.raises(ValueError):
        RandomHealthPolicy(1.1)
