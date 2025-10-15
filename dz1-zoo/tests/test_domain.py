import pytest
from domain.predator import Predator
from domain.herbo import Herbo
from domain.thing import Thing

def test_predator_validation():
    with pytest.raises(ValueError):
        Predator(name="", food=1)
    with pytest.raises(ValueError):
        Predator(name="Волк", food=-1)

def test_inventory_number_animal_once():
    a = Predator(name="Тигр", food=7)
    assert a.number == 0
    a.number = 10
    assert a.number == 10
    with pytest.raises(ValueError):
        a.number = 11

def test_thing_inventory_number_once():
    t = Thing(title="Стол")
    t.number = 5
    assert t.number == 5
    with pytest.raises(ValueError):
        t.number = 6

def test_herbo_kindness_and_petting():
    h1 = Herbo(name="Кролик", food=1, kindness=6)
    assert h1.is_petting_candidate() is True
    h2 = Herbo(name="Коза", food=1, kindness=5)
    assert h2.is_petting_candidate() is False
    with pytest.raises(ValueError):
        Herbo(name="Ошибка1", food=1, kindness=11)
    with pytest.raises(ValueError):
        Herbo(name="Ошибка2", food=1, kindness=-1)

def test_display_names():
    a = Predator(name="Тигр", food=5)
    t = Thing(title="Стол")
    assert a.display_name() == "Predator Тигр"
    assert t.display_name() == "Thing Стол"