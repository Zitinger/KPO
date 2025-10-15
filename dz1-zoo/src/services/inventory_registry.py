from domain.i_inventory import IInventory

class InventoryRegistry:
    def __init__(self, start_from=1):
        if start_from <= 0:
            raise ValueError("Стартовый номер должен быть положительным")
        self._next = start_from
        self._items = {}

    def register(self, item: IInventory) -> int:
        num = self._next
        self._next += 1
        item.number = num
        self._items[num] = item
        return num

    def list_items(self):
        result = []
        for n in sorted(self._items.keys()):
            obj = self._items[n]
            if hasattr(obj, "display_name"):
                label = obj.display_name()
            else:
                label = obj.__class__.__name__
            result.append((n, label))
        return result
