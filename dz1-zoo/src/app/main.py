from di.container import Container
from services.inventory_registry import InventoryRegistry
from services.zoo_service import ZooService
from services.random_health_policy import RandomHealthPolicy
from domain.herbo import Herbo
from domain.predator import Predator
from domain.thing import Thing

def build_container():
    c = Container()
    c.register(InventoryRegistry, lambda _: InventoryRegistry(start_from=1))
    c.register("health_policy", lambda _: RandomHealthPolicy(healthy_prob=0.9))
    c.register(ZooService, lambda ct: ZooService(
        health_policy=ct.resolve("health_policy"),
        inventory=ct.resolve(InventoryRegistry),
    ))
    return c

def ask_int(text, min_value=None, max_value=None):
    while True:
        try:
            v = int(input(text).strip())
            if min_value is not None and v < min_value:
                print(f"Значение должно быть не меньше {min_value}")
                continue
            if max_value is not None and v > max_value:
                print(f"Значение должно быть не больше {max_value}")
                continue
            return v
        except ValueError:
            print("Введите целое число")

def add_animal_ui(zoo):
    print("\n1) Травоядное")
    print("2) Хищник")
    t = input("Выберите вид: ").strip()
    if not (t  == "1" or t == "2"):
        print("Неизвестная опция")
        return
    name = input("Имя: ").strip()
    food = ask_int("Еда кг/день (≥0): ", 0)
    if t == "1":
        kindness = ask_int("Доброта [0..10]: ", 0, 10)
        animal = Herbo(name=name, food=food, kindness=kindness)
    elif t == "2":
        animal = Predator(name=name, food=food)
    if zoo.admit_animal(animal):
        print(f"Принято: #{animal.number} {animal.display_name()}")
    else:
        print(f"Отклонено ветклиникой: {animal.display_name()}")

def add_thing_ui(zoo):
    title = input("Название предмета: ").strip()
    thing = Thing(title=title)
    num = zoo.add_thing(thing)
    print(f"Добавлено: #{num} {thing.display_name()}")

def reports_ui(zoo):
    print("\n___ Отчёты ___")
    print(f"Животных: {len(zoo.animals)}")
    print(f"Суммарная еда кг/день: {zoo.total_food_per_day()}")
    print("Кандидаты в контактный зоопарк:")
    for a in zoo.petting_candidates():
        print(f"  - #{a.number} {a.display_name()} (доброта={a.kindness})")
    if len(zoo.petting_candidates) == 0:
        print("Кандидатов нет")
    print("\nИнвентарь:")
    for n, label in zoo.inventory_report():
        print(f"  - #{n} {label}")

def main():
    container = build_container()
    zoo = container.resolve(ZooService)
    print("Добро пожаловать в систему зоопарка!\n")
    while True:
        print("1) Добавить животное")
        print("2) Добавить предмет")
        print("3) Отчёты")
        print("0) Выход")
        choice = input("Выберите действие: ").strip()
        if choice == "1":
            add_animal_ui(zoo)
        elif choice == "2":
            add_thing_ui(zoo)
        elif choice == "3":
            reports_ui(zoo)
        elif choice == "0":
            break
        else:
            print("Неизвестная команда")

if __name__ == "__main__":
    main()
