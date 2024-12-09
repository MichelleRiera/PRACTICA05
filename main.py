from pedido import Pedido
from gestor import GestorPedidos
from inventario import Inventario
import multiprocessing

# Función para procesar pedidos
def procesar_pedidos(gestor_pedidos, inventario, barrier, lock):
    pedidos_no_procesados = []

    while not gestor_pedidos.pedidos_queue.empty():
        pedido = gestor_pedidos.pedidos_queue.get()
        pedido.estado = "en preparación"
        pedido.imprimir_estado()

        puede_procesarse = True
        with lock:  # Bloqueo para proteger actualizaciones concurrentes
            for item, cantidad in pedido.items.items():
                if not inventario.actualizar_inventario(item, cantidad):
                    print(f"No se pudo procesar el pedido {pedido.pedido_id}. Falta de stock para {item}.")
                    puede_procesarse = False
                    break

        if puede_procesarse:
            pedido.estado = "completado"
        else:
            pedido.estado = "no procesado"
            pedidos_no_procesados.append(pedido)

        pedido.imprimir_estado()

        # Mostrar inventario actualizado después de procesar cada pedido
        print("\nInventario Actualizado:")
        with lock:  # Bloqueo para acceso seguro al inventario
            for item, cantidad in inventario.consultar_inventario().items():
                print(f"{item}: {cantidad} disponibles")

        # Sincronización para que todos los procesos lleguen aquí antes de continuar
        barrier.wait()

    # Mostrar pedidos no procesados
    print("\nPedidos no procesados:")
    for pedido in pedidos_no_procesados:
        print(f"Pedido {pedido.pedido_id}: {pedido.items}")

# Función para generar pedidos predefinidos
def generar_pedidos(gestor_pedidos):
    pedidos_predefinidos = [
        {"pizza": 5, "hamburguesa": 2},
        {"hamburguesa": 5, "soda": 5},
        {"pizza": 3, "soda": 10},
    ]

    for pedido_id, items in enumerate(pedidos_predefinidos, start=1):
        pedido = Pedido(pedido_id, items)
        gestor_pedidos.recibir_pedido(pedido)

# Flujo principal
def flujo_principal():
    stock_inicial = {"pizza": 10, "hamburguesa": 15, "soda": 20}
    inventario = Inventario(stock_inicial)
    gestor_pedidos = GestorPedidos()
    barrier = multiprocessing.Barrier(2)  # Sincronizar 2 procesos
    lock = multiprocessing.Lock()  # Bloqueo para sincronización de datos

    # Mostrar inventario inicial
    print("Inventario Inicial:")
    for item, cantidad in inventario.consultar_inventario().items():
        print(f"{item}: {cantidad} disponibles")

    # Crear procesos
    procesos = []
    procesos.append(multiprocessing.Process(target=procesar_pedidos, args=(gestor_pedidos, inventario, barrier, lock)))

    # Generar pedidos
    generar_pedidos(gestor_pedidos)

    # Iniciar procesos
    for proceso in procesos:
        proceso.start()

    # Sincronizar procesos
    for proceso in procesos:
        proceso.join()

    # Mostrar inventario final
    print("\nEstado final del inventario:")
    for item, cantidad in inventario.consultar_inventario().items():
        print(f"{item}: {cantidad} disponibles")

if __name__ == "__main__":
    flujo_principal()
