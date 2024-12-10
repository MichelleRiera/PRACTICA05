import multiprocessing


class Inventario:
    def __init__(self, stock_inicial):
        """
        Clase que gestiona el inventario del restaurante.
        """
        self.stock = stock_inicial  # Diccionario simple
        self.lock = multiprocessing.Lock()

    def actualizar_inventario(self, item, cantidad):
        """
        Actualiza el inventario tras la preparación de un pedido.
        """
        with self.lock:
            if self.stock.get(item, 0) >= cantidad:
                self.stock[item] -= cantidad
                return True
            else:
                return False

    def consultar_inventario(self):
        """
        Devuelve el estado actual del inventario.
        """
        with self.lock:
            return dict(self.stock)
