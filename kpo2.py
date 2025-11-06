import itertools
import time
import json
import csv
import io
from datetime import datetime, date
from typing import List, Dict, Optional, Any

class DIContainer:
    def __init__(self):
        self._deps = {}
    def register(self, name, obj):
        self._deps[name] = obj
    def get(self, name):
        return self._deps.get(name)

class IdGenerator:
    def __init__(self, start=1):
        self._gen = itertools.count(start)
    def next(self):
        return next(self._gen)

_account_id_gen = IdGenerator(1001)
_category_id_gen = IdGenerator(1)
_operation_id_gen = IdGenerator(1)

class BankAccount:
    def __init__(self, name: str, balance: float = 0.0):
        self.id = _account_id_gen.next()
        self.name = name
        self.balance = float(balance)
    def __repr__(self):
        return f"<Account {self.id} {self.name} {self.balance}>"

class Category:
    def __init__(self, name: str, typ: str):
        self.id = _category_id_gen.next()
        self.name = name
        self.type = typ
    def __repr__(self):
        return f"<Category {self.id} {self.name} {self.type}>"

class Operation:
    def __init__(self, typ: str, bank_account_id: int, amount: float, date_: Optional[date]=None, description: str = "", category_id: Optional[int]=None):
        self.id = _operation_id_gen.next()
        self.type = typ
        self.bank_account_id = bank_account_id
        self.amount = float(amount)
        self.date = date_ or datetime.now().date()
        self.description = description
        self.category_id = category_id
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "bank_account_id": self.bank_account_id,
            "amount": self.amount,
            "date": self.date.isoformat(),
            "description": self.description,
            "category_id": self.category_id
        }
    def __repr__(self):
        return f"<Op {self.id} {self.type} {self.amount} acc={self.bank_account_id}>"

class DomainFactory:
    def create_account(self, name: str, balance: float = 0.0) -> BankAccount:
        if not name:
            raise ValueError("Account name required")
        return BankAccount(name, balance)
    def create_category(self, name: str, typ: str) -> Category:
        if typ not in ("income","expense"):
            raise ValueError("Category type must be 'income' or 'expense'")
        if not name:
            raise ValueError("Category name required")
        return Category(name, typ)
    def create_operation(self, typ: str, bank_account_id: int, amount: float, date_: Optional[date]=None, description: str="", category_id: Optional[int]=None) -> Operation:
        if typ not in ("income","expense"):
            raise ValueError("Operation type must be 'income' or 'expense'")
        if amount < 0:
            raise ValueError("Amount must be non-negative")
        return Operation(typ, bank_account_id, amount, date_, description, category_id)

class InMemoryRepo:
    def __init__(self):
        self.accounts: Dict[int, BankAccount] = {}
        self.categories: Dict[int, Category] = {}
        self.operations: Dict[int, Operation] = {}
    def add_account(self, acc: BankAccount):
        self.accounts[acc.id] = acc
    def get_account(self, acc_id: int) -> Optional[BankAccount]:
        return self.accounts.get(acc_id)
    def update_account(self, acc: BankAccount):
        self.accounts[acc.id] = acc
    def delete_account(self, acc_id: int):
        self.accounts.pop(acc_id, None)
    def list_accounts(self) -> List[BankAccount]:
        return list(self.accounts.values())
    def add_category(self, cat: Category):
        self.categories[cat.id] = cat
    def get_category(self, cat_id: int) -> Optional[Category]:
        return self.categories.get(cat_id)
    def list_categories(self) -> List[Category]:
        return list(self.categories.values())
    def add_operation(self, op: Operation):
        self.operations[op.id] = op
    def get_operation(self, op_id: int) -> Optional[Operation]:
        return self.operations.get(op_id)
    def list_operations(self) -> List[Operation]:
        return list(self.operations.values())

class RepoProxy:
    def __init__(self, repo: InMemoryRepo):
        self._repo = repo
        self._cache_accounts = None
        self._cache_categories = None
    def add_account(self, acc: BankAccount):
        self._repo.add_account(acc)
        self._cache_accounts = None
    def get_account(self, acc_id: int) -> Optional[BankAccount]:
        return self._repo.get_account(acc_id)
    def list_accounts(self) -> List[BankAccount]:
        if self._cache_accounts is None:
            self._cache_accounts = self._repo.list_accounts()
        return self._cache_accounts
    def add_category(self, cat: Category):
        self._repo.add_category(cat)
        self._cache_categories = None
    def list_categories(self) -> List[Category]:
        if self._cache_categories is None:
            self._cache_categories = self._repo.list_categories()
        return self._cache_categories
    def add_operation(self, op: Operation):
        self._repo.add_operation(op)

class AccountFacade:
    def __init__(self, repo: RepoProxy):
        self.repo = repo
    def create(self, account: BankAccount):
        self.repo.add_account(account)
    def get(self, acc_id: int):
        return self.repo.get_account(acc_id)
    def list(self):
        return self.repo.list_accounts()
    def delete(self, acc_id: int):
        self.repo._repo.delete_account(acc_id)

class CategoryFacade:
    def __init__(self, repo: RepoProxy):
        self.repo = repo
    def create(self, category: Category):
        self.repo.add_category(category)
    def list(self):
        return self.repo.list_categories()
    def get(self, cid: int):
        return self.repo._repo.get_category(cid)
    def delete(self, cid: int):
        self.repo._repo.categories.pop(cid, None)

class OperationFacade:
    def __init__(self, repo: RepoProxy):
        self.repo = repo
    def add(self, op: Operation):
        acc = self.repo.get_account(op.bank_account_id)
        if acc is None:
            raise ValueError("Account not found")
        if op.type == "income":
            acc.balance += op.amount
        else:
            acc.balance -= op.amount
        self.repo._repo.update_account(acc)
        self.repo.add_operation(op)
    def list(self):
        return self.repo._repo.list_operations()

class FinanceAnalyticsFacade:
    def __init__(self, repo: RepoProxy):
        self.repo = repo
    def balance_of(self, acc_id: int) -> float:
        acc = self.repo.get_account(acc_id)
        return acc.balance if acc else 0.0
    def diff_income_expense(self, from_date: date, to_date: date) -> float:
        ops = self.repo._repo.list_operations()
        income = sum(o.amount for o in ops if o.type == "income" and from_date <= o.date <= to_date)
        expense = sum(o.amount for o in ops if o.type == "expense" and from_date <= o.date <= to_date)
        return income - expense
    def group_by_category(self, from_date: date, to_date: date) -> Dict[str, float]:
        ops = self.repo._repo.list_operations()
        res: Dict[str, float] = {}
        for o in ops:
            if not (from_date <= o.date <= to_date):
                continue
            cat = self.repo._repo.get_category(o.category_id) if o.category_id else None
            key = (cat.name if cat else "Uncategorized")
            res.setdefault(key, 0.0)
            res[key] += o.amount if o.type == "expense" else o.amount
        return res

class Command:
    def execute(self):
        raise NotImplementedError()

class TimeMeasureDecorator(Command):
    def __init__(self, command: Command):
        self._command = command
    def execute(self):
        start = time.perf_counter()
        result = self._command.execute()
        end = time.perf_counter()
        print(f"[TIMING] {self._command.__class__.__name__} executed in {(end-start):.6f}s")
        return result

class AddAccountCommand(Command):
    def __init__(self, account_facade: AccountFacade, account: BankAccount):
        self.facade = account_facade
        self.account = account
    def execute(self):
        self.facade.create(self.account)
        return self.account

class ImportTemplate:
    def load(self, stream: io.TextIOBase):
        raw = stream.read()
        items = self.parse(raw)
        return items
    def parse(self, raw: str) -> List[Dict[str,Any]]:
        raise NotImplementedError()

class JSONImport(ImportTemplate):
    def parse(self, raw: str) -> List[Dict[str,Any]]:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data.get("operations", [])
        if isinstance(data, list):
            return data
        return []

class CSVImport(ImportTemplate):
    def parse(self, raw: str) -> List[Dict[str,Any]]:
        f = io.StringIO(raw)
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]

class ExportVisitor:
    def visit(self, accounts: List[BankAccount], categories: List[Category], operations: List[Operation]) -> str:
        raise NotImplementedError()

class JSONExportVisitor(ExportVisitor):
    def visit(self, accounts, categories, operations):
        data = {
            "accounts": [ {"id":a.id,"name":a.name,"balance":a.balance} for a in accounts],
            "categories": [ {"id":c.id,"name":c.name,"type":c.type} for c in categories],
            "operations": [o.to_dict() for o in operations]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

class CSVExportVisitor(ExportVisitor):
    def visit(self, accounts, categories, operations):
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["type","id","bank_account_id","amount","date","description","category_id"])
        for o in operations:
            w.writerow([o.type,o.id,o.bank_account_id,o.amount,o.date.isoformat(),o.description,o.category_id or ""])
        return out.getvalue()

def iso_to_date(s: str) -> date:
    return datetime.fromisoformat(s).date()

def import_operations_from_json(repo: RepoProxy, factory: DomainFactory, json_text: str):
    importer = JSONImport()
    items = importer.parse(json_text)
    for it in items:
        typ = it.get("type")
        acc_id = int(it.get("bank_account_id"))
        amount = float(it.get("amount"))
        date_ = iso_to_date(it.get("date")) if it.get("date") else None
        desc = it.get("description","")
        cat = int(it.get("category_id")) if it.get("category_id") else None
        op = factory.create_operation(typ, acc_id, amount, date_, desc, cat)
        repo.add_operation(op)

def export_all(repo: RepoProxy, format_: str) -> str:
    accounts = repo.list_accounts()
    categories = repo.list_categories()
    operations = repo._repo.list_operations()
    if format_ == "json":
        return JSONExportVisitor().visit(accounts,categories,operations)
    return CSVExportVisitor().visit(accounts,categories,operations)

def _prompt_int(prompt: str, default: Optional[int]=None) -> int:
    while True:
        s = input(prompt).strip()
        if s == "" and default is not None:
            return default
        try:
            return int(s)
        except:
            print("Введите число")

def _prompt_float(prompt: str, default: Optional[float]=None) -> float:
    while True:
        s = input(prompt).strip()
        if s == "" and default is not None:
            return default
        try:
            return float(s)
        except:
            print("Введите число")

def main():
    di = DIContainer()
    repo = InMemoryRepo()
    proxy = RepoProxy(repo)
    factory = DomainFactory()
    di.register("repo", proxy)
    di.register("factory", factory)
    di.register("account_facade", AccountFacade(proxy))
    di.register("category_facade", CategoryFacade(proxy))
    di.register("operation_facade", OperationFacade(proxy))
    di.register("analytics", FinanceAnalyticsFacade(proxy))
    print("=== Учёт финансов (мини) ===")
    while True:
        print("\n1) Создать счёт")
        print("2) Создать категорию")
        print("3) Добавить операцию")
        print("4) Показать счёта")
        print("5) Показать категории")
        print("6) Показать операции")
        print("7) Аналитика: разница за период")
        print("8) Экспорт данных (json/csv)")
        print("9) Импорт операций (json)")
        print("0) Выход")
        cmd = input("Выбор: ").strip()
        if cmd == "1":
            name = input("Название счёта: ").strip() or "Без имени"
            bal = _prompt_float("Начальный баланс: ", 0.0)
            acc = factory.create_account(name, bal)
            di.get("account_facade").create(acc)
            print(f"Создан счёт {acc.id} '{acc.name}' баланс={acc.balance}")
        elif cmd == "2":
            name = input("Название категории: ").strip() or "Без имени"
            typ = input("Тип (income/expense): ").strip().lower()
            try:
                cat = factory.create_category(name, typ)
                di.get("category_facade").create(cat)
                print(f"Создана категория {cat.id} '{cat.name}' тип={cat.type}")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd == "3":
            typ = input("Тип операции (income/expense): ").strip().lower()
            acc_id = _prompt_int("ID счёта: ")
            amt = _prompt_float("Сумма: ")
            cat_id_input = input("ID категории (enter если нет): ").strip()
            cat_id = int(cat_id_input) if cat_id_input else None
            desc = input("Описание: ").strip()
            try:
                op = factory.create_operation(typ, acc_id, amt, None, desc, cat_id)
                di.get("operation_facade").add(op)
                print("Операция добавлена", op)
            except Exception as e:
                print("Ошибка:", e)
        elif cmd == "4":
            for a in di.get("account_facade").list():
                print(f"{a.id}: {a.name} balance={a.balance}")
        elif cmd == "5":
            for c in di.get("category_facade").list():
                print(f"{c.id}: {c.name} ({c.type})")
        elif cmd == "6":
            for o in di.get("operation_facade").list():
                print(o.to_dict())
        elif cmd == "7":
            s = input("Дата с (YYYY-MM-DD): ").strip()
            t = input("Дата по (YYYY-MM-DD): ").strip()
            try:
                d1 = datetime.fromisoformat(s).date()
                d2 = datetime.fromisoformat(t).date()
                diff = di.get("analytics").diff_income_expense(d1,d2)
                print("Доходы - расходы =", diff)
                grouped = di.get("analytics").group_by_category(d1,d2)
                print("Группировка по категориям:")
                for k,v in grouped.items():
                    print(f"  {k}: {v}")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd == "8":
            fmt = input("Формат (json/csv): ").strip().lower()
            try:
                out = export_all(di.get("repo"), fmt)
                print(out)
            except Exception as e:
                print("Ошибка:", e)
        elif cmd == "9":
            path = input("Путь к json файлу: ").strip()
            try:
                with open(path, "r", encoding="utf-8") as f:
                    txt = f.read()
                    import_operations_from_json(di.get("repo"), factory, txt)
                    print("Импорт завершён")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd == "0":
            break
        else:
            print("Неверный ввод")

if __name__ == "__main__":
    main()
