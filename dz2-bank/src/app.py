from .container import Container
from .repositories.in_memory_account_repo import InMemoryAccountRepository
from .repositories.in_memory_category_repo import InMemoryCategoryRepository
from .repositories.in_memory_operation_repo import InMemoryOperationRepository
from .repositories.json_file_storage import JsonFileStorage
from .repositories.file_backed_repository_proxy import FileBackedRepositoryProxy
from .facades.account_facade import AccountFacade
from .facades.category_facade import CategoryFacade
from .facades.operation_facade import OperationFacade
from .facades.analytics_facade import AnalyticsFacade
from .menu import Menu
import os


class App:
    def __init__(self):
        self.container = Container()

    def run(self):
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        acc_repo = FileBackedRepositoryProxy(InMemoryAccountRepository(),
                                             JsonFileStorage(os.path.join(data_dir, "accounts.json")))
        cat_repo = FileBackedRepositoryProxy(InMemoryCategoryRepository(),
                                             JsonFileStorage(os.path.join(data_dir, "categories.json")))
        op_repo = FileBackedRepositoryProxy(InMemoryOperationRepository(),
                                            JsonFileStorage(os.path.join(data_dir, "operations.json")))
        self.container.register_instance("account_repo", acc_repo)
        self.container.register_instance("category_repo", cat_repo)
        self.container.register_instance("operation_repo", op_repo)
        self.container.register_instance("account_facade", AccountFacade(acc_repo))
        self.container.register_instance("category_facade", CategoryFacade(cat_repo))
        self.container.register_instance("operation_facade", OperationFacade(op_repo))
        self.container.register_instance("analytics_facade", AnalyticsFacade(acc_repo, cat_repo, op_repo))
        Menu(self.container).run()
