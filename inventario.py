import multiprocessing

class Inventario:
    def __init__(self, stock_inicial):
        self.stock = multiprocessing.Manager().dict(stock_inicial)
        self.lock = multiprocessing.Lock()

    def actualizar_inventario(self, item, cantidad):
        with self.lock:
            if self.stock[item] >= cantidad:
                self.stock[item] -= cantidad
                return True
            return False

    def consultar_inventario(self):
        with self.lock:
            return dict(self.stock)
