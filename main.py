from mpi4py import MPI
from pedido import Pedido
from gestor import GestorPedidos
from inventario import Inventario
from db_manager import DatabaseManager
import random

def generar_pedidos(num_pedidos=5):
    """Genera una lista de objetos Pedido con ítems aleatorios."""
    items_posibles = ["pizza", "hamburguesa", "soda", "papas", "ensalada"]
    pedidos = []
    for pedido_id in range(1, num_pedidos + 1):
        items_del_pedido = {}
        num_items = random.randint(1, 3)
        for _ in range(num_items):
            item = random.choice(items_posibles)
            cantidad = random.randint(1, 5)
            items_del_pedido[item] = items_del_pedido.get(item, 0) + cantidad
        pedidos.append(Pedido(pedido_id, items_del_pedido))
    return pedidos

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    if rank == 0:
        # Nodo 0: Maestro. Centraliza toda la impresión
        gestor = GestorPedidos()

        # En este ejemplo, no consultamos a la BD aún; 
        # si quieres mostrar el inventario inicial "global",
        # podrías pedírselo a rank=2 tras la inicialización.

        # Generar pedidos y mostrarlos en pantalla
        pedidos = generar_pedidos(num_pedidos=5)

        print("Inventario inicial (referencia local, si deseas consultarlo podrías hacerlo en rank=2)\n"
              "pizza: 50 disponibles\n"
              "hamburguesa: 40 disponibles\n"
              "soda: 60 disponibles\n"
              "papas: 30 disponibles\n"
              "ensalada: 25 disponibles\n")

        for pedido in pedidos:
            print(f"Pedido {pedido.pedido_id} registrado con los ítems: {pedido.items}")

        # Ahora, enviamos los pedidos a rank=1 de a uno
        for pedido in pedidos:
            comm.send(pedido, dest=1, tag=11)
            # Recibimos de rank=1 la "respuesta" (lista de cadenas) para imprimir
            respuesta = comm.recv(source=1, tag=12)
            # Imprimimos cada línea
            for linea in respuesta:
                print(linea)

        # Enviamos None para indicar fin
        comm.send(None, dest=1, tag=11)
        # Esperamos confirmación de rank=1
        comm.recv(source=1, tag=12)

        # ==== REPORTE FINAL ====
        print("\nReporte Final:")
        # 1) Consultamos pedidos a la BD
        todos_pedidos = gestor.consultar_pedidos_db()
        # 2) Consultamos inventario final a la BD
        inventario_final = gestor.consultar_inventario_db()

        # Filtrar por estado
        completados = [p for p in todos_pedidos if p[2] == "completado"]
        no_procesados = [p for p in todos_pedidos if p[2] == "no procesado"]

        # Imprimir reporte
        print("Pedidos completados exitosamente:")
        for p in completados:
            pedido_id = p[0]
            items_str = p[1]  # es un JSON string, si quieres parsear: json.loads(p[1])
            print(f"Pedido {pedido_id}: {items_str}")

        print("\nPedidos no procesados por falta de inventario:")
        for p in no_procesados:
            pedido_id = p[0]
            items_str = p[1]
            print(f"Pedido {pedido_id}: {items_str}")

        print("\nEstado final del inventario:")
        for item, stock in inventario_final.items():
            print(f"{item}: {stock} disponibles")

        # Enviar None a rank=2 para que termine su bucle (si lo deseas)
        comm.send(None, dest=2, tag=45)

    elif rank == 1:
        # Nodo 1: Procesa pedidos. 
        # En vez de imprimir "en vivo", retorna las cadenas a rank=0 para ser impresas en orden.
        inventario_local = Inventario({
            "pizza": 50,
            "hamburguesa": 40,
            "soda": 60,
            "papas": 30,
            "ensalada": 25
        })

        while True:
            pedido = comm.recv(source=0, tag=11)
            if pedido is None:
                # Enviamos confirmación a rank=0
                comm.send("done", dest=0, tag=12)
                break

            # Esta lista "logs" contendrá los mensajes que rank=0 imprimirá
            logs = []

            # Marcamos "en preparación"
            logs.append(f"\nPedido {pedido.pedido_id}: Estado actual -> en preparación")

            procesado_completamente = True
            for item, cantidad in pedido.items.items():
                if not inventario_local.actualizar_inventario_local(item, cantidad):
                    procesado_completamente = False
                    logs.append(f"No se pudo procesar el pedido {pedido.pedido_id}. Falta de stock para '{item}'.")
                    pedido.estado = "no procesado"
                    break

            if procesado_completamente:
                pedido.estado = "completado"
                logs.append(f"Pedido {pedido.pedido_id}: Estado actual -> completado")
                # Notificar a la BD
                for item, cant in pedido.items.items():
                    inventario_local.notificar_actualizacion_db(item, cant)
            else:
                logs.append(f"Pedido {pedido.pedido_id}: Estado actual -> no procesado")

            # Imprimimos el inventario local tras atender este pedido
            inv_str = "\nInventario actualizado:\n"
            for it, st in inventario_local.stock.items():
                inv_str += f"  {it}: {st} disponibles\n"
            logs.append(inv_str)

            # Registrar en la BD
            comm.send({
                "action": "REGISTRAR_PEDIDO",
                "data": {
                    "pedido_id": pedido.pedido_id,
                    "items": pedido.items,
                    "estado": pedido.estado
                }
            }, dest=2, tag=44)

            # Finalmente, enviamos a rank=0 los "logs" para ser impresos
            comm.send(logs, dest=0, tag=12)

    elif rank == 2:
        # Nodo 2: Base de datos
        db = DatabaseManager(db_name="pedidos", user="postgres", password="123", host="localhost", port=5432)
        db.connect()

        db.limpiar_tablas()

        inventario_inicial = {
            "pizza": 50,
            "hamburguesa": 40,
            "soda": 60,
            "papas": 30,
            "ensalada": 25
        }
        db.inicializar_inventario(inventario_inicial)

        while True:
            msg = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG)
            if msg is None:
                break

            if msg["action"] == "REGISTRAR_PEDIDO":
                data = msg["data"]
                db.registrar_pedido(data["pedido_id"], data["items"], data["estado"])

            elif msg["action"] == "ACTUALIZAR_INVENTARIO":
                db.actualizar_inventario(msg["data"]["item"], msg["data"]["cantidad"])

            elif msg["action"] == "CONSULTAR_PEDIDOS":
                comm.send(db.consultar_pedidos(), dest=0, tag=99)

            elif msg["action"] == "CONSULTAR_INVENTARIO":
                comm.send(db.consultar_inventario(), dest=0, tag=23)

        db.close()

if __name__ == "__main__":
    main()
