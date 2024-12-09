import multiprocessing
class GestorPedidos:
    def __init__(self):
        self.pedidos_queue = multiprocessing.Queue()

    def recibir_pedido(self, pedido):
        self.pedidos_queue.put(pedido)
        print(f"\nPedido {pedido.pedido_id} registrado con los ítems: {pedido.items}")
