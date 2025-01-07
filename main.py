from mpi4py import MPI
from pedido import Pedido
from gestor import GestorPedidos
from inventario import Inventario
import random
import json  # Por si quieres manipular (load/dump) el string JSON de items.

def generar_pedidos(num_pedidos=100):
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

    # =============== RANK 0 ===============
    if rank == 0:
        gestor = GestorPedidos()

        # Generar y distribuir pedidos
        pedidos = generar_pedidos(num_pedidos=100)
        print("\n=== [RANK 0] GENERANDO PEDIDOS ===\n")
        for pedido in pedidos:
            print(f"Pedido {pedido.pedido_id} con ítems: {pedido.items}")
            comm.send(pedido, dest=1, tag=11)
            # Recibir logs de rank=1
            logs = comm.recv(source=1, tag=12)
            for log in logs:
                print(log)

        # Finalizar distribución
        comm.send(None, dest=1, tag=11)
        comm.recv(source=1, tag=12)  # Confirmación de finalización

        # Generar el reporte final
        print("\n=== REPORTE FINAL ===")
        comm.send({"action": "CONSULTAR_PEDIDOS"}, dest=2, tag=45)
        pedidos_db = comm.recv(source=2, tag=45)

        comm.send({"action": "CONSULTAR_INVENTARIO"}, dest=2, tag=23)
        inventario_db = comm.recv(source=2, tag=23)

        completados = [p for p in pedidos_db if p[2] == "completado"]
        parciales = [p for p in pedidos_db if p[2] == "parcial"]
        no_proc = [p for p in pedidos_db if p[2] == "no procesado"]

        # Mostrar el reporte
        print("\nPedidos completados:")
        for p in completados:
            print(f"  Pedido {p[0]}: {p[1]}")
        print("\nPedidos procesados parcialmente:")
        for p in parciales:
            print(f"  Pedido {p[0]}: {p[1]}")
        print("\nPedidos no procesados:")
        for p in no_proc:
            print(f"  Pedido {p[0]}: {p[1]}")
        print("\n=== Inventario final ===")
        for item, stock in inventario_db.items():
            print(f"  {item}: {stock} disponibles")

    # =============== RANK 1 ===============
    elif rank == 1:
        comm.send({"action": "CONSULTAR_INVENTARIO"}, dest=2, tag=23)
        inventario_bd = comm.recv(source=2, tag=23)
        inventario_local = Inventario(inventario_bd)

        logs_inicio = ["\n=== [RANK 1] INVENTARIO LOCAL CARGADO ==="]
        for item, stock in inventario_local.stock.items():
            logs_inicio.append(f"  {item}: {stock} disponibles")
        comm.send(logs_inicio, dest=0, tag=12)

        while True:
            pedido = comm.recv(source=0, tag=11)
            if pedido is None:
                comm.send("done", dest=0, tag=12)
                break

            logs = [f"\n=== Procesando Pedido {pedido.pedido_id} ==="]
            procesados = {}
            no_procesados = {}

            for item, cantidad in pedido.items.items():
                stock_actual = inventario_local.stock.get(item, 0)
                if stock_actual >= cantidad:
                    inventario_local.stock[item] -= cantidad
                    procesados[item] = cantidad
                else:
                    no_procesados[item] = cantidad

            if len(procesados) == len(pedido.items):
                pedido.estado = "completado"
            elif len(procesados) == 0:
                pedido.estado = "no procesado"
            else:
                pedido.estado = "parcial"

            logs.append(f"Estado final del pedido: {pedido.estado}")
            logs.append(f"Ítems procesados: {procesados}")
            logs.append(f"Ítems no procesados: {no_procesados}")

            if procesados:
                for item, cantidad in procesados.items():
                    comm.send({
                        "action": "ACTUALIZAR_INVENTARIO",
                        "data": {"item": item, "cantidad": cantidad}
                    }, dest=2, tag=44)

            comm.send({
                "action": "REGISTRAR_PEDIDO",
                "data": {"pedido_id": pedido.pedido_id, "items": pedido.items, "estado": pedido.estado}
            }, dest=2, tag=44)

            comm.send(logs, dest=0, tag=12)

    # =============== RANK 2 ===============
    elif rank == 2:
        import psycopg2
        from db_manager import DatabaseManager

        db = DatabaseManager(db_name="pedidos", user="postgres", password="123", host="localhost", port=5432)
        db.connect()
        db.limpiar_tablas()

        inventario_inicial = {
            "pizza": 80,
            "hamburguesa": 50,
            "soda": 60,
            "papas": 20,
            "ensalada": 95
        }
        db.inicializar_inventario(inventario_inicial)

        while True:
            status = MPI.Status()
            msg = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
            if msg is None:
                break

            action = msg.get("action", None)

            if action == "REGISTRAR_PEDIDO":
                data = msg["data"]
                db.registrar_pedido(data["pedido_id"], data["items"], data["estado"])

            elif action == "ACTUALIZAR_INVENTARIO":
                item = msg["data"]["item"]
                cantidad = msg["data"]["cantidad"]
                db.actualizar_inventario(item, cantidad)

            elif action == "CONSULTAR_PEDIDOS":
                pedidos_db = db.consultar_pedidos()
                comm.send(pedidos_db, dest=status.Get_source(), tag=45)

            elif action == "CONSULTAR_INVENTARIO":
                inventario_db = db.consultar_inventario()
                comm.send(inventario_db, dest=status.Get_source(), tag=23)

        db.close()


if __name__ == "__main__":
    main()
