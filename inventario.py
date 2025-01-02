from mpi4py import MPI

class Inventario:
    """
    Clase que maneja el inventario local en rank=1 y notifica al rank=2
    cuando se actualiza el inventario en la base de datos.
    """
    def __init__(self, stock_inicial=None):
        self.stock = stock_inicial if stock_inicial else {}
        self.comm = MPI.COMM_WORLD

    def actualizar_inventario_local(self, item, cantidad):
        """
        Disminuye el stock local si hay suficiente. Retorna True si se pudo, False en caso contrario.
        """
        stock_actual = self.stock.get(item, 0)
        if stock_actual >= cantidad:
            self.stock[item] = stock_actual - cantidad
            return True
        return False

    def notificar_actualizacion_db(self, item, cantidad):
        """
        Notifica al nodo de base de datos (rank=2) la actualización de inventario.
        """
        update_msg = {
            "action": "ACTUALIZAR_INVENTARIO",
            "data": {"item": item, "cantidad": cantidad}
        }
        self.comm.send(update_msg, dest=2, tag=22)
