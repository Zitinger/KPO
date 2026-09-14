# Домашнее задание №2 - Банковский учет
#### Дьяков Иван Михайлович - БПИ 244
*Паттерны проектирования.*

---

## Обзор проекта

```
dz2-bank/
  main.py                  # точка входа (создает App и запускает меню)

  src/
    app.py                 # сборка приложения: DI-контейнер, репозитории, фасады, запуск Menu
    container.py           # DI-контейнер (registry инстансов)

    domain/                # сущности предметной области и enum'ы
      bank_account.py
      category.py
      operation.py
      category_type.py
      operation_type.py

    ids/
      id_generator.py      # генерация UID для новых объектов

    factory/
      entity_factory.py    # единая фабрика создания сущностей + базовая валидация

    repositories/          # репозитории и хранение снапшотов
      repository.py        # абстрактный интерфейс репозитория (abc)
      in_memory_account_repo.py
      in_memory_category_repo.py
      in_memory_operation_repo.py
      json_file_storage.py
      file_backed_repository_proxy.py   # Proxy: слой поверх InMemory

    facades/               # фасады
      account_facade.py
      category_facade.py
      operation_facade.py  # поддерживает OperationBuilder и пересчет баланса
      analytics_facade.py  # простая аналитика: доход-расход, по категориям

    commands/              # Команда + Декоратор (замер времени)
      command.py
      simple_command.py
      timing_decorator.py
      invoker.py

    importers/             # Шаблонный метод для импорта
      base_importer.py
      json_importer.py
      yaml_importer.py
      csv_importer.py

    exporters/             # visitor для экспорта
      exportable_data.py
      export_visitor.py
      json_export_visitor.py
      yaml_export_visitor.py
      csv_export_visitor.py

    strategies/            # Strategy: выбор импортера/экспортера по расширению
      import_resolver.py
      export_resolver.py

    builders/              # Builder: пошаговая сборка операции
      operation_builder.py

  requirements.txt
  .gitignore
```
---

## Общая идея и изменения относительно тз
Реализована мини-система учета финансов с CRUD по счетам/категориям/операциям, аналитикой (доход-расход, группировка по категориям) и импортом/экспортом в файлы.

Изменения относительно тз:
- Добавлен CSV-импорт единым файлом из трех секций
- Добавлен выбор импортера/экспортера по расширению через Strategy
- Добавлен Builder для пошагового создания операций (в качестве 8го паттерна проектирования)
- Опциональный замер времени выполенения сценариев через декоратор - нефункциональная фича, не влияющая на доменную логику

---

## Domain

- **BankAccount** - счет (id, name, balance).  
- **Category** - категория операции (id, type, name), где type это income/expense.  
- **Operation** - операция (доход/расход): id, type, bank_account_id, amount, date, description, category_id.  
- **CategoryType / OperationType** - enum’ы для типов.

Сущности простые: только данные и минимальные классы (валидация в фабрике).

---

## Создание объектов (Factory) и Builder

- **EntityFactory**: единая точка создания BankAccount, Category, Operation.
  Приводит строковые "income" / "expense" к enum (устраняет ошибки типов при импорте).
  Валидирует сумму (amount > 0), баланс (balance >= 0).

- **OperationBuilder**: пошаговая сборка Operation без длинных конструкторов:  
  `with_type(...) → with_account(...) → with_amount(...) → with_date(...) → with_category(...) → with_description(...) → build()`.

---

## Хранилища и репозитории

- **InMemoryXXXRepository** - базовые репозитории в памяти.  
- **FileBackedRepositoryProxy** - Proxy над InMemory: загружает объекты из JSON при старте, сохраняет при изменениях.  
- **JsonFileStorage** - примитивное файловое хранилище.

Интерфейс репозитория - через абстрактный базовый класс `Repository` (методы add/get/update/delete/all/snapshot).

---

## Facades

- **AccountFacade** - CRUD по счетам.  
- **CategoryFacade** - CRUD по категориям.  
- **OperationFacade** - CRUD по операциям, билдер операций и пересчет баланса по операциям.  
- **AnalyticsFacade** - разница доходы–расходы за период; агрегирование по категориям.

---

## Меню и запуск

Весь пользовательский ввод/вывод сосредоточен в `Menu`.  
`main.py` только создает `App`, а `App` собирает зависимости и запускает меню.

```
pip install -r requirements.txt
python main.py
```

---

## Импорт / Экспорт

### Импорт: JSON, YAML, CSV  
Шаблонный метод (BaseImporter) + реализация под формат файла.  
При импорте создаются новые id для счетов/категорий, а операции перепривязываются по id.

- **JSON/YAML**: ожидаются поля `accounts[]`, `categories[]`, `operations[]`. Типы `"income"/"expense"` допускаются строками - фабрика приведет к enum.  
- **CSV**: поддержан единый файл из трех секций.

Минимальный формат CSV (совместим с экспортом тройкой CSV-файлов):
```txt
#accounts
id,name,balance
a1,Кошелек,0

#categories
id,type,name
c1,income,Зарплата
c2,expense,Еда

#operations
id,type,bank_account_id,amount,date,description,category_id
o1,income,a1,1000,2025-11-01,,c1
o2,expense,a1,200,2025-11-02,обед,c2
```

### Экспорт: JSON, YAML, CSV  
Реализован через **Visitor**: `ExportableData.accept(visitor, path)`.  
Выбор формата - **Strategy** по расширению/ключу (json/yaml/csv).  
CSV-экспорт создает три файла: *\*_accounts.csv*, *\*_categories.csv*, *\*_operations.csv*.

---

## SOLID и GRASP

### SOLID

#### **S - Single Responsibility (единственная ответственность)**
- каждый класс решает одну задачу (например, EntityFactory - только создание объектов; Menu - только UI-поток и тд...)

#### **O - Open/Closed (открыт для расширения, закрыт для модификации)**
- новые форматы экспорта/импорта добавляются через новые визиторы/импортеры, без правок ExportableData/BaseImporter

#### **L - Liskov Substitution (подстановка Барбары Лисков)**
- все репозитории заменяемы по интерфейсу Repository

#### **I - Interface Segregation (разделение интерфейсов)**
- узкие интерфейсы - приложение опирается на Repository

#### **D - Dependency Inversion (инверсия зависимостей)**
- высокоуровневые модули (фасады/меню) зависят от абстракций (Repository, визиторы, резолверы), связывание идет через App/Container

### GRASP
- **Controller**: Menu координирует сценарии приложения
- **Creator**: EntityFactory создает доменные объекты, т.к. знает их инварианты
- **Low Coupling / High Cohesion**: хранение и доменная логика разделены; прокси отвечает только за взаимодействие с пользователем
- **Indirection**: FileBackedRepositoryProxy как прослойка между доменом и файловым форматом
- **Polymorphism**: семейства импортеров/экспортеров выбираются по интерфейсу
- **Pure Fabrication**: ExportableData/визиторы - искусственные классы для снижения связности и соблюдения OCP
- **Protected Variations**: выбор стратегии по расширению изолирует вариативность форматов
---

## Паттерны GoF и обоснование

- **Factory** - `EntityFactory` централизует создание сущностей + валидацию и приведение типов (уменьшает дублирование и ошибки).  
- **Builder** - `OperationBuilder` снимает большие конструкторы у Operation, упрощает пошаговый ввод с консоли.  
- **Facade** - фасады сценариев (`Account/Category/Operation/Analytics`Facade) упрощают сценарии для UI, скрывая детали репозиториев/валидации.  
- **Strategy** - `ImportResolver` / `ExportResolver` (выбор реализации по расширению файла).  
- **Template Method** - `BaseImporter` (общий каркас импорта с заменяемой стадией парсинга (минимум дублирования).  
- **Visitor** - экспортеры (добавляем форматы экспорта, не трогая данные).  
- **Proxy** - `FileBackedRepositoryProxy` (прозрачно добавляет персистентность над InMemory (подмена реализации без изменений клиентов)).  
- **Command** - унифицированное выполнение сценариев, возможность оберток.  
- **Decorator** - `TimingDecorator` (сквозной замер времени поверх команд без правок бизнес-кода).

Итого 9 паттернов.

---

## Итог

Проект реализует разделение ответственности, сборку зависимостей в одном месте и набор классических GoF‑паттернов. Форматы импорта/экспорта и замер времени подключены как легко заменяемые стратегии/декораторы, без вмешательства в доменную логику.

ㅤ

ㅤ

ㅤ

ㅤ

###### это было потно