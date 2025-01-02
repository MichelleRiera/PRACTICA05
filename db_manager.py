import psycopg2
import json
import os

os.environ["PYTHONUTF8"] = "1"

class DatabaseManager:
    def __init__(self, db_name="pedidos", user="postgres", password="123", host="localhost", port=5432):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                options="-c client_encoding=UTF8"
            )
           # print(f"Conexión establecida a la base de datos '{self.db_name}'.")
            self.conn.autocommit = True
            self.create_tables()
        except psycopg2.Error as e:
            #print(f"Error al conectar a la base de datos: {e}")
            raise e

    def create_tables(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pedidos (
                        pedido_id INT PRIMARY KEY,
                        items TEXT,
                        estado VARCHAR(20)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inventario (
                        item VARCHAR(50) PRIMARY KEY,
                        stock INT
                    );
                """)
            #print("Tablas verificadas o creadas correctamente.")
        except psycopg2.Error as e:
            #print(f"Error al crear tablas: {e}")
            raise e

    def inicializar_inventario(self, stock_inicial):
        try:
            with self.conn.cursor() as cursor:
                for item, stock in stock_inicial.items():
                    cursor.execute("""
                        INSERT INTO inventario (item, stock)
                        VALUES (%s, %s)
                        ON CONFLICT (item) DO NOTHING;
                    """, (item, stock))
            #print("Inventario inicializado en la base de datos.")
        except psycopg2.Error as e:
            #print(f"Error al inicializar inventario: {e}")
            raise e

    def registrar_pedido(self, pedido_id: int, items: dict, estado: str):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pedidos WHERE pedido_id = %s", (pedido_id,))
                if cursor.fetchone():
                    raise ValueError(f"El pedido con ID {pedido_id} ya existe.")
                items_encoded = json.dumps(items, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO pedidos (pedido_id, items, estado)
                    VALUES (%s, %s, %s)
                """, (pedido_id, items_encoded, estado))
               # print(f"Pedido {pedido_id} registrado correctamente con estado '{estado}'.")
        except psycopg2.Error as e:
            #print(f"Error al registrar pedido: {e}")
            raise e

    def actualizar_inventario(self, item: str, cantidad: int):
        """
        Disminuye el stock de 'item' en 'cantidad', sólo si hay suficiente stock.
        Retorna True si se actualizó, False si no.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE inventario
                    SET stock = stock - %s
                    WHERE item = %s AND stock >= %s
                """, (cantidad, item, cantidad))
                if cursor.rowcount > 0:
                   # print(f"Inventario actualizado para el item '{item}' en -{cantidad}.")
                    return True
                else:
                    #print(f"No se pudo actualizar inventario para '{item}' (stock insuficiente).")
                    return False
        except psycopg2.Error as e:
            #print(f"Error al actualizar inventario: {e}")
            raise e

    def consultar_pedidos(self):
        """ Devuelve todos los pedidos en forma de lista de tuplas (pedido_id, items, estado). """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM pedidos;")
                rows = cursor.fetchall()
                #print(f"Pedidos consultados: {len(rows)} registros encontrados.")
                return rows
        except psycopg2.Error as e:
            #print(f"Error al consultar pedidos: {e}")
            raise e

    def consultar_inventario(self):
        """ Devuelve un diccionario con {item: stock} """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT item, stock FROM inventario;")
                rows = cursor.fetchall()
                #print(f"Inventario consultado: {len(rows)} registros encontrados.")
                return {item: stock for (item, stock) in rows}
        except psycopg2.Error as e:
           # print(f"Error al consultar inventario: {e}")
            raise e

    def limpiar_tablas(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE pedidos RESTART IDENTITY CASCADE;")
                cursor.execute("TRUNCATE TABLE inventario RESTART IDENTITY CASCADE;")
           # print("Tablas 'pedidos' e 'inventario' limpiadas correctamente.")
        except psycopg2.Error as e:
            #print(f"Error al limpiar las tablas: {e}")
            raise e

    def close(self):
        if self.conn:
            self.conn.close()
            #print("Conexión cerrada.")
