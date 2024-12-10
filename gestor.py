import multiprocessing
from pedido import Pedido


class GestorPedidos(multiprocessing.Process):
    def __init__(self, pedidos_queue, inventario, lock, reporte):
        """
        Clase que gestiona la recepción y procesamiento de pedidos.
        """
        super().__init__()
        self.pedidos_queue = pedidos_queue
        self.inventario = inventario
        self.lock = lock
        self.reporte = reporte

    def recibir_pedido(self, pedido):
        """
        Agrega un pedido a la cola.
        """
        if pedido is not None:
            print(f"Pedido {pedido.pedido_id} registrado con los ítems: {pedido.items}")
        self.pedidos_queue.put(pedido)

    def procesar_pedido(self):
        """
        Extrae un pedido de la cola, lo marca como "en preparación" y actualiza el inventario.
        """
        while True:
            pedido = self.pedidos_queue.get()
            if pedido is None:
                # Señal de que no hay más pedidos
                break

            pedido.estado = "en preparación"
            pedido.imprimir_estado()

            puede_procesarse = True
            with self.lock:
                for item, cantidad in pedido.items.items():
                    if not self.inventario.actualizar_inventario(item, cantidad):
                        print(f"No se pudo procesar el pedido {pedido.pedido_id}. Falta de stock para {item}.")
                        puede_procesarse = False
                        break

            if puede_procesarse:
                pedido.estado = "completado"
                self.reporte["completados"].append(pedido)
            else:
                pedido.estado = "no procesado"
                self.reporte["no_procesados"].append(pedido)

            pedido.imprimir_estado()

            print("\nInventario actualizado:")
            for item, cantidad in self.inventario.consultar_inventario().items():
                print(f"{item}: {cantidad} disponibles")

    def run(self):
        """
        Procesa los pedidos recibidos en la cola.
        """
        self.procesar_pedido()
