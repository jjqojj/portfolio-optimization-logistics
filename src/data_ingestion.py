import pandas as pd
import duckdb
import os

class BogotaDataIngestion:
    """
    Clase encargada de la creacion de estructuras e ingestion automatizada de datasets (CSV)
    hacia el Almacen de Datos Analitico (DuckDB), garantizando idempotencia.
    """
    def __init__(self, db_path: str = "data/logistic_warehouse.db", raw_dir: str = "data/raw"):
        self.db_path = db_path
        self.raw_dir = raw_dir
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def __get_connection(self):
        """Metodo privado para establecer conexion con el motor de DuckDB."""
        return duckdb.connect(self.db_path)

    def create_schema_if_not_exists(self):
        """Paso de Cimentacion (DDL): Crea la estructura fisica de las tablas."""
        print("[DATABASE] Verifying and configuring relational schema...")
        conn = self.__get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dim_customers (
                    customer_id INTEGER PRIMARY KEY,
                    customer_name VARCHAR,
                    location_latitude DOUBLE,
                    location_longitude DOUBLE,
                    zone_bogota VARCHAR
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dim_vehicles (
                    vehicle_id INTEGER PRIMARY KEY,
                    plate_number VARCHAR,
                    max_weight_kg DOUBLE,
                    max_volume_m3 DOUBLE
                );
            """)
            print("[SUCCESS] Relational structures verified and ready.")
        finally:
            conn.close()

    def ingest_dim_customers(self):
        """Lee e inyecta los datos de clientes aplicando sobreescritura limpia."""
        csv_path = os.path.join(self.raw_dir, "dim_customers.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing required raw file: {csv_path}")
            
        print("[INGESTION] Processing dim_customers.csv...")
        df_customers = pd.read_csv(csv_path)
        
        conn = self.__get_connection()
        try:
            conn.execute("DELETE FROM dim_customers;")
            conn.execute("INSERT INTO dim_customers SELECT * FROM df_customers;")
            
            # CORRECCION: Separar la consulta para evitar el error de 'NoneType'
            cursor = conn.execute("SELECT COUNT(*) FROM dim_customers;")
            result = cursor.fetchone()
            
            count = result[0] if result is not None else 0
            print(f"[SUCCESS] Ingested {count} records into dim_customers table.")
        finally:
            conn.close()

    def ingest_dim_vehicles(self):
        """Lee e inyecta los datos de la flota de vehiculos."""
        csv_path = os.path.join(self.raw_dir, "dim_vehicles.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing required raw file: {csv_path}")
            
        print("[INGESTION] Processing dim_vehicles.csv...")
        df_vehicles = pd.read_csv(csv_path)
        
        conn = self.__get_connection()
        try:
            conn.execute("DELETE FROM dim_vehicles;")
            conn.execute("INSERT INTO dim_vehicles SELECT * FROM df_vehicles;")
            
            # CORRECCION: Separar la consulta para evitar el error de 'NoneType'
            cursor = conn.execute("SELECT COUNT(*) FROM dim_vehicles;")
            result = cursor.fetchone()
            
            count = result[0] if result is not None else 0
            print(f"[SUCCESS] Ingested {count} records into dim_vehicles table.")
        finally:
            conn.close()

    def run_pipeline(self):
        """Orquestador maestro de la fase de ingestion."""
        print("[INFO] Starting Data Ingestion Pipeline...")
        self.create_schema_if_not_exists()
        self.ingest_dim_customers()
        self.ingest_dim_vehicles()
        print("[INFO] Data Ingestion Pipeline completed successfully.")

if __name__ == "__main__":
    pipeline = BogotaDataIngestion()
    pipeline.run_pipeline()