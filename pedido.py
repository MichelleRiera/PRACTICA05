class Pedido:
    def __init__(self, pedido_id, items):
        """
        Clase que representa un pedido.
        """
        self.pedido_id = pedido_id
        self.items = items
        self.estado = "pendiente"

    def imprimir_estado(self):
        """
        Muestra el estado actual del pedido.
        """
        print(f"Pedido {self.pedido_id}: Estado actual -> {self.estado}")
