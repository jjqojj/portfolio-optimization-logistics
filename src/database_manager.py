import duckdb
import os

class LogisticsDatabaseManager:
    """
    Clase encargada de la gobernanza, inicializacion y gestion de consultas
    de la base de datos analitica de Logistica Bogota Express.
    """
    def __init__(self, db_filename: str = "logistic_warehouse.db"):
        """
        Metodo Constructor. Define el estado inicial del objeto.
        """
        # Definimos la ruta donde se guardara el archivo fisico de la base de datos
        # Usamos la carpeta 'data/processed/' para almacenar el archivo analitico
        self.db_path = os.path.join("data", "processed", db_filename)
        
        # ENCAPSULAMIENTO: Al usar doble guion bajo (__conn), convertimos la conexion
        # en un atributo PRIVADO. Ningun script externo podra cerrar o corromper
        # la conexion directo sin pasar por los metodos oficiales de esta clase.
        self.__conn = None

    def connect(self):
        """
        Establece una conexion persistente con el archivo binario de DuckDB.
        """
        try:
            # Inicializamos la conexion y la guardamos en el atributo encapsulado
            self.__conn = duckdb.connect(database=self.db_path)
            print(f"[SUCCESS] Connected securely to analytical engine at: {self.db_path}")
        except Exception as e:
            print(f"[ERROR] Failed to establish database boundary connection: {e}")
            raise

    def initialize_schema(self):
        """
        Ejecuta las instrucciones DDL de SQL para materializar el diseno
        que aprobamos formalmente en la Task 1 (Star Schema).
        """
        if self.__conn is None:
            raise ConnectionError("[ERROR] Database connection is vacant. Execute .connect() first.")

        print("[INFO] Initializing relational database structures...")

        # 1. Tabla de Dimension: Clientes (dim_customers)
        self.__conn.execute("""
            CREATE TABLE IF NOT EXISTS dim_customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name VARCHAR NOT NULL,
                location_latitude DOUBLE NOT NULL,
                location_longitude DOUBLE NOT NULL,
                zone_bogota VARCHAR NOT NULL
            );
        """)

        # 2. Tabla de Dimension: Flota de Vehiculos (dim_vehicles)
        self.__conn.execute("""
            CREATE TABLE IF NOT EXISTS dim_vehicles (
                vehicle_id INTEGER PRIMARY KEY,
                plate_number VARCHAR NOT NULL,
                max_weight_kg DOUBLE NOT NULL,
                max_volume_m3 DOUBLE NOT NULL
            );
        """)

        # 3. Tabla de Hechos: Ordenes Diarias (fact_orders)
        self.__conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                weight_kg DOUBLE NOT NULL,
                volume_m3 DOUBLE NOT NULL,
                ready_time_mins INTEGER NOT NULL,
                due_time_mins INTEGER NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
                FOREIGN KEY (vehicle_id) REFERENCES dim_vehicles(vehicle_id)
            );
        """)
        print("[SUCCESS] Relational topology (Star Schema) instantiated perfectly.")

    def close(self):
        """
        Cierra de forma segura los flujos de memoria de la conexion.
        """
        if self.__conn:
            self.__conn.close()
            print("[INFO] Database connection closed safely.")


# --- BLOQUE DE VERIFICACION LOCAL ---
# Este bloque solo se ejecuta si corres este archivo directamente en la terminal.
# Funciona para validar que tu objeto se comporta como esperas.
if __name__ == "__main__":
    # Instanciamos el objeto (Construimos la casa a partir del plano)
    manager = LogisticsDatabaseManager()
    
    # Operamos el objeto a traves de sus metodos abstractos
    manager.connect()
    manager.initialize_schema()
    manager.close()