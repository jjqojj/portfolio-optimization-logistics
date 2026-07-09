import duckdb
import pandas as pd


try:
    database_name = 'data/processed/logistic_warehouse.db'
    con = duckdb.connect(database_name)
    print(f"[SUCESS] correct conection: {database_name}\n")

  
    print("--- TABLES ---")
    tablas = con.sql("SHOW TABLES").df() # .df() lo convierte a DataFrame de Pandas
    
    if tablas.empty:
        print("[TABLES EMPTY] The tables areempty.")
    else:
        print(tablas)
        print("\n---------------------------\n")

        columna_nombre_tabla = tablas.columns[0] 
        
        for tabla in tablas[columna_nombre_tabla]:
            query = f"SELECT * FROM {tabla}"
            df_contenido = con.sql(query).df()
            
            print(df_contenido)
            print("-" * 50)

    con.close()

except Exception as e:
    print(f"[ERROR] It was not possible to read the database: {e}")