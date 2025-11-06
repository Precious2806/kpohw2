import unittest
from kpo2 import DIContainer, InMemoryRepo, RepoProxy, DomainFactory, AccountFacade, CategoryFacade, OperationFacade, FinanceAnalyticsFacade, BankAccount, Category, Operation
from datetime import date, timedelta

class TestFactoryAndRepo(unittest.TestCase):
    def setUp(self):
        self.factory = DomainFactory()
    def test_create_account(self):
        acc = self.factory.create_account("Main", 100.0)
        self.assertEqual(acc.name, "Main")
        self.assertEqual(acc.balance, 100.0)
    def test_create_category_invalid(self):
        with self.assertRaises(ValueError):
            self.factory.create_category("X", "unknown")
    def test_create_operation_negative(self):
        with self.assertRaises(ValueError):
            self.factory.create_operation("income", 1, -5)

class TestFacadesAndOperations(unittest.TestCase):
    def setUp(self):
        repo = InMemoryRepo()
        self.proxy = RepoProxy(repo)
        self.factory = DomainFactory()
        self.acc = self.factory.create_account("A", 1000.0)
        self.proxy.add_account(self.acc)
        self.cat_income = self.factory.create_category("Salary","income")
        self.cat_expense = self.factory.create_category("Food","expense")
        self.proxy.add_category(self.cat_income)
        self.proxy.add_category(self.cat_expense)
        self.account_facade = AccountFacade(self.proxy)
        self.category_facade = CategoryFacade(self.proxy)
        self.operation_facade = OperationFacade(self.proxy)
    def test_add_income_operation_updates_balance(self):
        op = self.factory.create_operation("income", self.acc.id, 500.0, date.today(), "pay", self.cat_income.id)
        self.operation_facade.add(op)
        a = self.proxy.get_account(self.acc.id)
        self.assertAlmostEqual(a.balance, 1500.0)
    def test_add_expense_operation_updates_balance(self):
        op = self.factory.create_operation("expense", self.acc.id, 200.0, date.today(), "buy", self.cat_expense.id)
        self.operation_facade.add(op)
        a = self.proxy.get_account(self.acc.id)
        self.assertAlmostEqual(a.balance, 800.0)
    def test_list_operations(self):
        op1 = self.factory.create_operation("income", self.acc.id, 100.0, date.today(), "", self.cat_income.id)
        op2 = self.factory.create_operation("expense", self.acc.id, 50.0, date.today(), "", self.cat_expense.id)
        self.operation_facade.add(op1)
        self.operation_facade.add(op2)
        ops = self.operation_facade.list()
        self.assertEqual(len(ops), 2)

class TestAnalytics(unittest.TestCase):
    def setUp(self):
        repo = InMemoryRepo()
        self.proxy = RepoProxy(repo)
        self.factory = DomainFactory()
        self.acc = self.factory.create_account("A", 0.0)
        self.proxy.add_account(self.acc)
        self.cat1 = self.factory.create_category("Salary","income")
        self.cat2 = self.factory.create_category("Food","expense")
        self.proxy.add_category(self.cat1)
        self.proxy.add_category(self.cat2)
        self.opf = OperationFacade(self.proxy)
        today = date.today()
        op1 = self.factory.create_operation("income", self.acc.id, 1000.0, today - timedelta(days=2), "", self.cat1.id)
        op2 = self.factory.create_operation("expense", self.acc.id, 100.0, today - timedelta(days=1), "", self.cat2.id)
        self.opf.add(op1)
        self.opf.add(op2)
        self.analytics = FinanceAnalyticsFacade(self.proxy)
    def test_diff_income_expense(self):
        d1 = date.today() - timedelta(days=5)
        d2 = date.today()
        diff = self.analytics.diff_income_expense(d1,d2)
        self.assertAlmostEqual(diff, 900.0)
    def test_group_by_category(self):
        d1 = date.today() - timedelta(days=5)
        d2 = date.today()
        grouped = self.analytics.group_by_category(d1,d2)
        self.assertIn("Salary", grouped)
        self.assertIn("Food", grouped)

if __name__ == "__main__":
    unittest.main()
