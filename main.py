from gestor import GestorPedidos
from inventario import Inventario
from pedido import Pedido
import multiprocessing


def generar_pedidos(gestor_pedidos):
    pedidos_simulados = [
        {"pizza": 5, "hamburguesa": 2},
        {"hamburguesa": 5, "soda": 5},
        {"pizza": 3, "soda": 10},
        {"pizza": 5, "soda": 5},
    ]

    for pedido_id, items in enumerate(pedidos_simulados, start=1):
        pedido = Pedido(pedido_id, items)
        gestor_pedidos.recibir_pedido(pedido)

    # Señal para indicar que no hay más pedidos
    gestor_pedidos.recibir_pedido(None)


def flujo_principal():
    manager = multiprocessing.Manager()
    stock_inicial = {"pizza": 10, "hamburguesa": 15, "soda": 20}
    inventario = Inventario(stock_inicial)
    pedidos_queue = multiprocessing.Queue()
    lock = multiprocessing.Lock()

    # Estructura para el reporte final (usando Manager)
    reporte = manager.dict({
        "completados": manager.list(),
        "no_procesados": manager.list(),
    })

    # Mostrar inventario inicial
    print("Inventario inicial:")
    for item, cantidad in inventario.consultar_inventario().items():
        print(f"{item}: {cantidad} disponibles")

    # Crear el proceso de GestorPedidos
    gestor_pedidos = GestorPedidos(pedidos_queue, inventario, lock, reporte)
    gestor_pedidos.start()

    # Generar pedidos en el flujo principal
    generar_pedidos(gestor_pedidos)

    # Esperar a que el gestor termine
    gestor_pedidos.join()

    # Mostrar reporte final
    print("\nReporte Final:")
    print("Pedidos completados exitosamente:")
    for pedido in reporte["completados"]:
        print(f"Pedido {pedido.pedido_id}: {pedido.items}")

    print("\nPedidos no procesados por falta de inventario:")
    for pedido in reporte["no_procesados"]:
        print(f"Pedido {pedido.pedido_id}: {pedido.items}")

    print("\nEstado final del inventario:")
    for item, cantidad in inventario.consultar_inventario().items():
        print(f"{item}: {cantidad} disponibles")


if __name__ == "__main__":
    flujo_principal()
