#!/usr/bin/env python3
"""
Logística Bogotá Express - Operational Spatial Analytics Framework
Task 06: Time-Dependent Traffic Simulation Engine
"""

import os
import duckdb
import pandas as pd


class TrafficSimulationEngine:
    """
    Transforms static physical distances into dynamic, time-dependent travel time
    matrices based on Bogota's micro-congestion zones and temporal windows.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.source_distance_table = "fact_distance_matrix"
        self.target_time_table = "fact_time_matrix"
        
        # Base kinematics configuration (Reference velocity: 40 km/h -> Factor: 1.5 min/km)
        self.km_to_minutes_factor = 1.5

        # Hardcoded CEDI parameters for safe mapping fallback
        self.cedi_id = 0
        self.cedi_zone = "Fontibon"

    def load_spatial_and_distance_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads the static distance matrix and customer zone catalogs from DuckDB.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database core missing at: {self.db_path}")

        print(f"[TRAFFIC ADAPTER] Connecting to analytical core: {self.db_path}")
        conn = duckdb.connect(self.db_path)

        try:
            # 1. Fetch static distance array computed in Task 05
            dist_query = f"SELECT origin_node_id, destination_node_id, distance_km FROM {self.source_distance_table};"
            df_distances = conn.execute(dist_query).df()

            # 2. Fetch customer zones to inject spatial friction attributes
            zone_query = "SELECT customer_id, zone_bogota FROM dim_customers;"
            df_zones = conn.execute(zone_query).df()

            print(f"[TRAFFIC ADAPTER] Data loaded. Distances pairs: {len(df_distances)}, Zone mappings: {len(df_zones)}")
            return df_distances, df_zones

        except Exception as e:
            raise RuntimeError(f"Failed to query source matrices from warehouse: {str(e)}")
        finally:
            conn.close()

    def simulate_dynamic_traffic(self, df_distances: pd.DataFrame, df_zones: pd.DataFrame) -> pd.DataFrame:
        """
        Applies time-dependent and asymmetric zone congestion coefficients to 
        transform linear kilometers into operational travel minutes.
        """
        print("[TRAFFIC ENGINE] Initializing multi-window spatiotemporal simulations...")

        # Create a dictionary for rapid O(1) zone lookups, enforcing CEDI baseline zone
        zone_lookup = dict(zip(df_zones["customer_id"], df_zones["zone_bogota"]))
        zone_lookup[self.cedi_id] = self.cedi_zone

        # Base kinematic conversion to flat minutes
        df_distances["base_time_min"] = df_distances["distance_km"] * self.km_to_minutes_factor

        # Map destination zones explicitly to evaluate asymmetric friction
        df_distances["dest_zone"] = df_distances["destination_node_id"].map(zone_lookup)

        # Definition of Time-Dependent Traffic Matrix Records
        time_records = []

        # Operational Scenarios Loop
        scenarios = [
            {"time_window": "off_peak", "alpha_general": 1.0, "high_density_penalty": 0.0},
            {"time_window": "mid_day", "alpha_general": 1.4, "high_density_penalty": 0.0},
            {"time_window": "rush_hour", "alpha_general": 2.2, "high_density_penalty": 0.5}
        ]

        for sc in scenarios:
            window = sc["time_window"]
            alpha_g = sc["alpha_general"]
            gamma_p = sc["high_density_penalty"]

            print(f"[TRAFFIC ENGINE] Processing scenario branch: {window.upper()} (Alpha={alpha_g})")

            for _, row in df_distances.iterrows():
                dest_zone = row["dest_zone"]
                base_time = row["base_time_min"]

                # Evaluate asymmetric spatial bottleneck criteria
                is_high_density = dest_zone in ["Chapinero", "Usaquen"]
                alpha_final = alpha_g + (gamma_p if is_high_density else 0.0)

                # Final time-dependent minute projection
                travel_time_min = base_time * alpha_final

                time_records.append({
                    "origin_node_id": int(row["origin_node_id"]),
                    "destination_node_id": int(row["destination_node_id"]),
                    "time_window": window,
                    "travel_time_min": float(travel_time_min)
                })

        return pd.DataFrame(time_records)

    def persist_time_matrix(self, df_time_matrix: pd.DataFrame) -> None:
        """
        Persists the multi-window dynamic time metrics into DuckDB targets.
        """
        print(f"[DATA TARGET] Writing dynamic records to table: {self.target_time_table}")
        conn = duckdb.connect(self.db_path)

        try:
            with conn:
                # Create relational schema for the dynamic time matrix
                conn.execute(
                    f"""
                    CREATE OR REPLACE TABLE {self.target_time_table} (
                        origin_node_id INTEGER,
                        destination_node_id INTEGER,
                        time_window VARCHAR,
                        travel_time_min DOUBLE,
                        PRIMARY KEY (origin_node_id, destination_node_id, time_window)
                    );
                """
                )
                
                # Bulk insert from pandas layer
                conn.execute(f"INSERT INTO {self.target_time_table} SELECT * FROM df_time_matrix")

                # Transactional safety verification
                result = conn.execute(f"SELECT COUNT(*) FROM {self.target_time_table}").fetchone()
                record_count = result[0] if result is not None else 0
                print(f"[DATA TARGET] Transaction committed successfully. Records persisted: {record_count}")

        except Exception as e:
            raise RuntimeError(f"Database error during traffic matrix persistence: {str(e)}")
        finally:
            conn.close()

    def execute_pipeline(self) -> None:
        """
        Runs the complete execution pipeline for Task 06.
        """
        print("\n" + "=" * 80)
        print("STARTING PIPELINE: TIME-DEPENDENT TRAFFIC SIMULATION ENGINE")
        print("=" * 80)

        df_distances, df_zones = self.load_spatial_and_distance_data()
        df_time_matrix = self.simulate_dynamic_traffic(df_distances, df_zones)
        self.persist_time_matrix(df_time_matrix)

        print("=" * 80)
        print("PIPELINE EXECUTION SUCCESSFUL - TASK 06 COMPLETE")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    # Define repository connection path
    DATABASE_PATH = os.path.join("data/processed", "logistic_warehouse.db")

    # Fire runtime engine pipeline
    engine = TrafficSimulationEngine(db_path=DATABASE_PATH)
    engine.execute_pipeline()