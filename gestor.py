from mpi4py import MPI

class GestorPedidos:
    """
    Clase encargada de enviar pedidos (desde rank=0) y de consultar
    pedidos en la DB (haciendo uso de MPI para comunicarse con rank=2).
    """
    def __init__(self, db_rank=2):
        self.comm = MPI.COMM_WORLD
        self.db_rank = db_rank

    def recibir_pedido(self, pedido):
        """
        Envía el pedido al rank=1 para que se procese.
        """
        self.comm.send(pedido, dest=1, tag=11)
        print(f"[Nodo 0] Enviando Pedido {pedido.pedido_id} al nodo 1.")

    def consultar_pedidos_db(self):
        """
        Solicita la lista de pedidos a la base de datos (rank=2).
        """
        self.comm.send({"action": "CONSULTAR_PEDIDOS"}, dest=self.db_rank, tag=99)
        pedidos = self.comm.recv(source=self.db_rank, tag=99)
        return pedidos

    def consultar_inventario_db(self):
        """
        Solicita el estado actual del inventario a la base de datos (rank=2).
        """
        self.comm.send({"action": "CONSULTAR_INVENTARIO"}, dest=self.db_rank, tag=23)
        inventario = self.comm.recv(source=self.db_rank, tag=23)
        return inventario
