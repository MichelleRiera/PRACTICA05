from mpi4py import MPI
from pedido import Pedido
from gestor import GestorPedidos
from inventario import Inventario
import random
import json  # Por si quieres manipular (load/dump) el string JSON de items.

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

    # =============== RANK 0 ===============
    if rank == 0:
        # Nodo 0 (Maestro): Genera pedidos, centraliza la impresión y lanza el reporte final
        gestor = GestorPedidos()

        # Generar pedidos y listarlos en pantalla
        pedidos = generar_pedidos(num_pedidos=30)
        print("\n=== [RANK 0] GENERANDO PEDIDOS ===\n")
        for pedido in pedidos:
            print(f"Pedido {pedido.pedido_id} con ítems: {pedido.items}")

        # Enviar pedidos uno a uno al nodo 1
        for pedido in pedidos:
            comm.send(pedido, dest=1, tag=11)
            # Recibir logs de rank=1 para imprimir en orden
            respuesta = comm.recv(source=1, tag=12)
            for linea in respuesta:
                print(linea)

        # Indicar fin de pedidos a rank=1
        comm.send(None, dest=1, tag=11)
        # Esperar confirmación
        comm.recv(source=1, tag=12)

        # ======= REPORTE FINAL =======
        print("\n=== REPORTE FINAL ===")
        # 1) Consultar pedidos en la BD (rank=2)
        pedidos_db = gestor.consultar_pedidos_db()
        # 2) Consultar inventario final en la BD
        inventario_db = gestor.consultar_inventario_db()

        # Filtrar pedidos por estado
        completados = [p for p in pedidos_db if p[2] == "completado"]
        parciales   = [p for p in pedidos_db if p[2] == "parcial"]
        no_proc     = [p for p in pedidos_db if p[2] == "no procesado"]

        # Mostrar
        print("\nPedidos completados:")
        for p in completados:
            pedido_id = p[0]
            items_str = p[1]
            print(f"  Pedido {pedido_id}: {items_str}")

        print("\nPedidos procesados parcialmente:")
        for p in parciales:
            pedido_id = p[0]
            items_str = p[1]
            print(f"  Pedido {pedido_id}: {items_str}")

        print("\nPedidos no procesados (ningún ítem):")
        for p in no_proc:
            pedido_id = p[0]
            items_str = p[1]
            print(f"  Pedido {pedido_id}: {items_str}")

        print("\n=== Inventario final en la BD ===")
        for item, stock in inventario_db.items():
            print(f"  {item}: {stock} disponibles")

        # Enviar None a rank=2 para terminar
        comm.send(None, dest=2, tag=45)

    # =============== RANK 1 ===============
    elif rank == 1:
        # Nodo 1 (Preparación): 
        # 1) Solicita el inventario inicial al nodo 2
        # 2) Procesa cada pedido (posible procesamiento parcial)
        # 3) Envía logs a rank=0 y actualizaciones a rank=2

        # Pedir el inventario inicial a rank=2
        comm.send({"action": "CONSULTAR_INVENTARIO"}, dest=2, tag=23)
        inventario_bd = comm.recv(source=2, tag=23)

        # Cargar el inventario local con lo que devolvió la BD
        inventario_local = Inventario(inventario_bd)
        
        # Enviar a rank=0 un log con el inventario inicial cargado
        logs_inicio = ["\n=== [RANK 1] INVENTARIO LOCAL CARGADO DESDE BD ==="]
        for it, st in inventario_local.stock.items():
            logs_inicio.append(f"  {it}: {st} disponibles")
        comm.send(logs_inicio, dest=0, tag=12)

        while True:
            pedido = comm.recv(source=0, tag=11)
            if pedido is None:
                # Enviamos confirmación a rank=0 de que no hay más pedidos
                comm.send("done", dest=0, tag=12)
                break

            # Aquí guardamos los mensajes para rank=0
            logs = []
            logs.append(f"\n=== Procesando Pedido {pedido.pedido_id} ===")
            logs.append(f"Pedido {pedido.pedido_id}: Estado actual -> en preparación")

            # Diccionarios para registrar qué ítems se procesan y cuáles no
            procesados     = {}
            no_procesados  = {}

            for item, cant in pedido.items.items():
                stock_actual = inventario_local.stock.get(item, 0)
                if stock_actual >= cant:
                    # Sí hay suficiente stock -> procesar
                    inventario_local.stock[item] = stock_actual - cant
                    procesados[item] = cant
                else:
                    # No hay stock suficiente -> no procesar ese ítem
                    no_procesados[item] = cant

            # Determinar estado del pedido
            if len(procesados) == 0:
                # Ningún ítem pudo procesarse
                pedido.estado = "no procesado"
                logs.append(f"Ningún ítem pudo procesarse en Pedido {pedido.pedido_id}.")
            elif len(procesados) == len(pedido.items):
                # Todos los ítems se procesaron
                pedido.estado = "completado"
                logs.append(f"Pedido {pedido.pedido_id}: Estado actual -> completado")
            else:
                # Se procesaron algunos ítems y otros no
                pedido.estado = "parcial"
                logs.append(f"Pedido {pedido.pedido_id}: Estado actual -> parcial")
                logs.append(f"Ítems sin stock: {no_procesados}")

            # Notificar a la BD solo de los ítems efectivamente procesados
            if len(procesados) > 0:
                for it, cantidad_procesada in procesados.items():
                    inventario_local.notificar_actualizacion_db(it, cantidad_procesada)

            # Construir string del inventario local actualizado
            inv_str = "\nInventario local actualizado:\n"
            for it, st in inventario_local.stock.items():
                inv_str += f"  {it}: {st} disponibles\n"
            logs.append(inv_str)

            # Registrar el pedido (sea completo, parcial o no procesado) en la BD
            comm.send({
                "action": "REGISTRAR_PEDIDO",
                "data": {
                    "pedido_id": pedido.pedido_id,
                    "items": pedido.items,   # ítems originales
                    "estado": pedido.estado
                }
            }, dest=2, tag=44)

            # Enviar los logs a rank=0
            comm.send(logs, dest=0, tag=12)

    # =============== RANK 2 ===============
    elif rank == 2:
        import psycopg2
        from db_manager import DatabaseManager

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
            # Recibir con un status para saber quién envió el mensaje
            status = MPI.Status()
            msg = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
            source_rank = status.Get_source()

            if msg is None:
                break

            action = msg.get("action", None)

            if action == "REGISTRAR_PEDIDO":
                data = msg["data"]
                db.registrar_pedido(data["pedido_id"], data["items"], data["estado"])

            elif action == "ACTUALIZAR_INVENTARIO":
                item = msg["data"]["item"]
                cant = msg["data"]["cantidad"]
                db.actualizar_inventario(item, cant)

            elif action == "CONSULTAR_PEDIDOS":
                pedidos_bd = db.consultar_pedidos()
                # Responder a quien lo solicitó (generalmente rank=0)
                comm.send(pedidos_bd, dest=source_rank, tag=99)

            elif action == "CONSULTAR_INVENTARIO":
                inventario_bd = db.consultar_inventario()
                # Responder a quien lo pidió (rank=1 u otro)
                comm.send(inventario_bd, dest=source_rank, tag=23)

        db.close()

if __name__ == "__main__":
    main()
