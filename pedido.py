class Pedido:
    def __init__(self, pedido_id, items):
        self.pedido_id = pedido_id
        self.items = items
        self.estado = "pendiente"

    def imprimir_estado(self):
        print(f"Pedido {self.pedido_id}: Estado actual -> {self.estado}")
