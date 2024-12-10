import multiprocessing


class Inventario:
    def __init__(self, stock_inicial):
        self.stock = stock_inicial  # Diccionario simple
        self.lock = multiprocessing.Lock()

    def actualizar_inventario(self, item, cantidad):
        with self.lock:
            if self.stock.get(item, 0) >= cantidad:
                self.stock[item] -= cantidad
                return True
            else:
                return False

    def consultar_inventario(self):
        with self.lock:
            return dict(self.stock)
