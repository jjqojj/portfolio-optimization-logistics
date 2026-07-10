#!/usr/bin/env python3
"""
Logística Bogotá Express - Operational Spatial Analytics Framework
Task 05: Compute Georeferenced Haversine Distance Matrix
"""

import os
import duckdb
import pandas as pd
import numpy as np


class HaversineDistanceMatrixCalculator:
    """
    Computes and persists an N x N distance matrix using the mathematically stable
    Haversine formula and computational two-argument arctangent (atan2).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.earth_radius_km = 6371.009  # Volumetric Earth Radius Constant
        self.matrix_table_name = "fact_distance_matrix"
        
        # Hardcoded CEDI Fontibón parameters to inject programmatically
        self.cedi_node = {
            "customer_id": 0,
            "customer_name": "Fontibon Depot (CEDI)",
            "location_latitude": 4.6758,
            "location_longitude": -74.1355,
            "zone_bogota": "Fontibon"
        }

    def fetch_spatial_nodes(self) -> pd.DataFrame:
        """
        Queries all operational nodes from DuckDB and injects the master CEDI node.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(
                f"Target database missing at: {self.db_path}. Execute data-engineering ingestion pipeline first."
            )

        print(f"[SPATIAL ADAPTER] Connecting to analytical core: {self.db_path}")
        conn = duckdb.connect(self.db_path)

        try:
            # Query extracting master customer nodes using exact CSV/DuckDB schema columns
            query = """
                SELECT 
                    customer_id,
                    customer_name,
                    location_latitude,
                    location_longitude,
                    zone_bogota
                FROM dim_customers
                ORDER BY customer_id ASC;
            """
            df_customers = conn.execute(query).df()
            
            # Programmatic injection of CEDI at index 0
            df_cedi = pd.DataFrame([self.cedi_node])
            df_nodes = pd.concat([df_cedi, df_customers], ignore_index=True)
            
            print(f"[SPATIAL ADAPTER] Successfully loaded {len(df_nodes)} active nodes (CEDI + {len(df_customers)} Clients).")
            return df_nodes
        except Exception as e:
            raise RuntimeError(f"Failed to query dim_customers table: {str(e)}")
        finally:
            conn.close()

    def compute_vectorized_haversine(self, df_nodes: pd.DataFrame) -> pd.DataFrame:
        """
        Executes highly efficient vectorized calculation of the asymmetric matrix
        leveraging NumPy floating-point meshgrids with exact schema columns.
        """
        print("[MATHEMATICAL ENGINE] Allocating meshgrids for spatial coordinate matrices...")

        # Extract coordinate arrays using exact schema mappings
        latitudes = df_nodes["location_latitude"].to_numpy()
        longitudes = df_nodes["location_longitude"].to_numpy()
        node_ids = df_nodes["customer_id"].to_numpy()

        # Step 1: Extrapolate Degrees to Radians
        lat_rad = np.radians(latitudes)
        lon_rad = np.radians(longitudes)

        # Build N x N spatial coordinate meshes
        lat_i, lat_j = np.meshgrid(lat_rad, lat_rad, indexing="ij")
        lon_i, lon_j = np.meshgrid(lon_rad, lon_rad, indexing="ij")

        # Step 2: Angular Delta Derivation
        delta_lat = lat_j - lat_i
        delta_lon = lon_j - lon_i

        # Step 3: Internal Chord Evaluation (a)
        a = (
            np.sin(delta_lat / 2.0) ** 2
            + np.cos(lat_i) * np.cos(lat_j) * np.sin(delta_lon / 2.0) ** 2
        )

        # Step 4: Spatial Arc Construction (c) via computational Two-Argument Arctangent
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

        # Step 5: Metric Distance Output
        distance_matrix = self.earth_radius_km * c

        # Transform raw N x N array into a long-format relational dataframe
        print("[MATHEMATICAL ENGINE] Transforming matrix structures to relational schema format...")
        records = []
        n = len(node_ids)

        for i in range(n):
            for j in range(n):
                records.append(
                    {
                        "origin_node_id": int(node_ids[i]),
                        "destination_node_id": int(node_ids[j]),
                        "distance_km": float(distance_matrix[i, j]),
                    }
                )

        return pd.DataFrame(records)

    def persist_distance_matrix(self, df_matrix: pd.DataFrame) -> None:
        """
        Persists the calculated distance metrics into DuckDB database targets.
        Ensures proper transactional commit boundaries to prevent NoneType fetch errors.
        """
        print(f"[DATA TARGET] Initializing overwrite stream on target table: {self.matrix_table_name}")
        
        # Open connection
        conn = duckdb.connect(self.db_path)

        try:
            # Using 'with conn:' forces DuckDB to handle transactional commits cleanly
            with conn:
                # Create or replace structured relational fact table
                conn.execute(
                    f"""
                    CREATE OR REPLACE TABLE {self.matrix_table_name} (
                        origin_node_id INTEGER,
                        destination_node_id INTEGER,
                        distance_km DOUBLE,
                        PRIMARY KEY (origin_node_id, destination_node_id)
                    );
                """
                )

                # Direct registration of pandas dataframe into DuckDB engine
                conn.execute(f"INSERT INTO {self.matrix_table_name} SELECT * FROM df_matrix")

                # Validate record count outside the insertion transaction block
                result = conn.execute(f"SELECT COUNT(*) FROM {self.matrix_table_name}").fetchone()
            
            if result is not None:
                record_count = result[0]
                print(f"[DATA TARGET] Execution Closeout. Table '{self.matrix_table_name}' contains {record_count} records.")
            else:
                print("[DATA TARGET] Warning: Verification query returned an empty result stream.")

        except Exception as e:
            raise RuntimeError(f"Database error during spatial matrix persistence: {str(e)}")
        finally:
            conn.close()

    def execute_pipeline(self) -> None:
        """
        Triggers the structural sequence flow for Task 05.
        """
        print("\n" + "=" * 80)
        print("STARTING PIPELINE: COMPUTE GEOREFERENCED HAVERSINE DISTANCE MATRIX")
        print("=" * 80)

        df_nodes = self.fetch_spatial_nodes()
        df_matrix = self.compute_vectorized_haversine(df_nodes)
        self.persist_distance_matrix(df_matrix)

        print("=" * 80)
        print("PIPELINE EXECUTION SUCCESSFUL - TASK 05 COMPLETE")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    # Path configuration targeting our localized data warehouse
    DATABASE_PATH = os.path.join("data/processed", "logistic_warehouse.db")

    # Instance instantiation and pipeline runtime orchestration
    calculator = HaversineDistanceMatrixCalculator(db_path=DATABASE_PATH)
    calculator.execute_pipeline()