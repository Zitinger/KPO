from .commands.invoker import Invoker
from .commands.simple_command import SimpleCommand
from .commands.timing_decorator import TimingDecorator
from .domain.category_type import CategoryType
from .domain.operation_type import OperationType
from .exporters.exportable_data import ExportableData
from .strategies.import_resolver import ImportResolver
from .strategies.export_resolver import ExportResolver


class Menu:
    def __init__(self, container):
        self.c = container
        self.invoker = Invoker()

    def run(self):
        while True:
            print("Меню")
            print("1. Счета")
            print("2. Категории")
            print("3. Операции")
            print("4. Аналитика")
            print("5. Импорт")
            print("6. Экспорт")
            print("7. Пересчет баланса")
            print("0. Выход")
            choice = input("Выберите действие: ").strip()
            if choice == "1":
                self._accounts()
            elif choice == "2":
                self._categories()
            elif choice == "3":
                self._operations()
            elif choice == "4":
                self._analytics()
            elif choice == "5":
                self._import()
            elif choice == "6":
                self._export()
            elif choice == "7":
                self._recalc()
            elif choice == "0":
                break
            else:
                print("Неверный номер действия")

    def _time(self, fn):
        def on_done(name, dt):
            print(f"Время: {dt:.6f}s")

        cmd = SimpleCommand(fn)
        dec = TimingDecorator(cmd, on_done)
        return self.invoker.run(dec)

    def _accounts(self):
        f = self.c.resolve("account_facade")
        while True:
            print("1. Создать")
            print("2. Список")
            print("3. Обновить")
            print("4. Удалить")
            print("0. Назад")
            k = input("Выберите действие: ").strip()
            if k == "1":
                name = input("Название: ")
                bal = float(input("Баланс: ") or "0")
                self._time(lambda: f.create(name, bal))
            elif k == "2":
                xs = self._time(lambda: f.list())
                for x in xs:
                    print(x.id, x.name, x.balance)
            elif k == "3":
                id = input("ID: ")
                name = input("Название(new, пусто чтобы пропустить): ") or None
                bal = input("Баланс(new, пусто чтобы пропустить): ")
                bal = float(bal) if bal else None
                self._time(lambda: f.update(id, name, bal))
            elif k == "4":
                id = input("ID: ")
                self._time(lambda: f.delete(id))
            elif k == "0":
                break
            else:
                print("Неверный номер действия")

    def _categories(self):
        f = self.c.resolve("category_facade")
        while True:
            print("1. Создать")
            print("2. Список")
            print("3. Обновить")
            print("4. Удалить")
            print("0. Назад")
            k = input("Выберите действие: ").strip()
            if k == "1":
                t = input("Тип (income/expense): ").strip().lower()
                if t not in ["income", "expense"]:
                    print("Неверный ввод")
                    continue
                t = CategoryType.INCOME if t == "income" else CategoryType.EXPENSE
                name = input("Название: ")
                self._time(lambda: f.create(t, name))
            elif k == "2":
                xs = self._time(lambda: f.list())
                for x in xs:
                    print(x.id, x.type.value, x.name)
            elif k == "3":
                id = input("ID: ")
                name = input("Название(пусто чтобы пропустить): ") or None
                type_in = input("Тип(income/expense или пусто): ").strip().lower()
                t = None
                if type_in:
                    if t not in ["income", "expense"]:
                        print("Неверный ввод")
                        continue
                    t = CategoryType.INCOME if type_in == "income" else CategoryType.EXPENSE
                self._time(lambda: f.update(id, name, t))
            elif k == "4":
                id = input("ID: ")
                self._time(lambda: f.delete(id))
            elif k == "0":
                break

    def _operations(self):
        f = self.c.resolve("operation_facade")
        acc_repo = self.c.resolve("account_repo")
        cat_repo = self.c.resolve("category_repo")
        while True:
            print("1. Создать")
            print("2. Список")
            print("3. Обновить")
            print("4. Удалить")
            print("0. Назад")
            k = input("Выберите действие: ").strip()
            if k == "1":
                t = input("Тип (income/expense): ").strip().lower()
                if t not in ["income", "expense"]:
                    print("Неверный ввод")
                    continue
                t = OperationType.INCOME if t == "income" else OperationType.EXPENSE
                print("Счета:")
                for a in acc_repo.all(): print(a.id, a.name)
                ba = input("ID счета: ").strip()
                amt = float(input("Сумма: "))
                date = input("Дата (YYYY-MM-DD): ").strip()
                print("Категории:")
                for c in cat_repo.all(): print(c.id, c.type.value, c.name)
                ca = input("ID категории: ").strip() or None
                desc = input("Описание: ").strip() or None
                builder = f.builder().with_type(t).with_account(ba).with_amount(amt).with_date(date).with_category(
                    ca).with_description(desc)
                op = builder.build()
                self._time(lambda: f.add_op(op))
            elif k == "2":
                xs = self._time(lambda: f.list())
                for x in xs:
                    print(x.id, x.type.value, x.bank_account_id, x.amount, x.date, x.description, x.category_id)
            elif k == "3":
                id = input("ID: ")
                field = input("Поле для изменения: ")
                value = input("Новое значение: ")
                self._time(lambda: f.update(id, **{field: value}))
            elif k == "4":
                id = input("ID: ")
                self._time(lambda: f.delete(id))
            elif k == "0":
                break

    def _analytics(self):
        a = self.c.resolve("analytics_facade")
        print("1. Баланс доход-расход")
        print("2. Группировка по категориям")
        print("0. Назад")
        k = input("Выберите действие ").strip()
        if k == "1":
            df = input("От (YYYY-MM-DD, пусто): ").strip() or None
            dt = input("До (YYYY-MM-DD, пусто): ").strip() or None
            print(self._time(lambda: a.income_expense_diff(df, dt)))
        elif k == "2":
            cat_repo = self.c.resolve("category_repo")
            res = self._time(lambda: a.group_by_category())
            for cat_id, val in res.items():
                name = "unknown"
                if cat_id:
                    c = cat_repo.get(cat_id)
                    if c: name = c.name
                print(name, val)

    def _import(self):
        path = input("Путь к файлу (.json/.yaml/.yml/.csv): ").strip()
        imp = ImportResolver().resolve(path)
        acc_repo = self.c.resolve("account_repo")
        cat_repo = self.c.resolve("category_repo")
        op_repo = self.c.resolve("operation_repo")
        self._time(lambda: imp.import_file(path, acc_repo, cat_repo, op_repo))

    def _export(self):
        t = input("Формат (json/yaml/csv) или укажите расширение в имени файла: ").strip().lower()
        path = input("Путь для сохранения: ").strip()
        acc_repo = self.c.resolve("account_repo")
        cat_repo = self.c.resolve("category_repo")
        op_repo = self.c.resolve("operation_repo")
        data = ExportableData(acc_repo.snapshot(), cat_repo.snapshot(), op_repo.snapshot())
        v = ExportResolver().resolve(t or path)
        self._time(lambda: data.accept(v, path))

    def _recalc(self):
        f = self.c.resolve("operation_facade")
        acc_repo = self.c.resolve("account_repo")
        self._time(lambda: f.recalc_balance(acc_repo))
