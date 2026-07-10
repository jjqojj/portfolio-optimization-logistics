import os
import duckdb
import pandas as pd
from dataclasses import dataclass

@dataclass
class VRPTWDataModel:
    """
    Acts as the canonical data repository required by the MILP Solver.
    Transforms relational database fields into algebraic indexed sets.
    """
    nodes: list[int]             # Set V (0 = CEDI, 1..60 = Customers)
    customers: list[int]         # Set C (1..60)
    vehicles: list[int]          # Set K (Vehicle IDs)
    
    # Parameters
    demands: dict[int, float]          # q_i (Indexed by node)
    capacities: dict[int, float]       # Q_k (Indexed by vehicle)
    service_times: dict[int, float]    # s_i (Indexed by node)
    earliest_times: dict[int, float]   # e_i (Indexed by node)
    latest_times: dict[int, float]     # l_i (Indexed by node)
    travel_times: dict[tuple[int, int], float] # t_ij (Indexed by (origin, destination))

    @classmethod
    def from_warehouse(cls, db_path: str, time_window_scenario: str = "rush_hour"):
        """
        Factory method to extract, join and format warehouse entities into the dataclass.
        """
        conn = duckdb.connect(db_path)
        
        try:
            # 1. Extract sets
            df_cust = conn.execute("SELECT customer_id, zone_bogota FROM dim_customers ORDER BY customer_id;").df()
            df_veh = conn.execute("SELECT vehicle_id, capacity_kg FROM dim_vehicles;").df()
            
            # Fetch dynamic times for the chosen scenario
            time_query = f"""
                SELECT origin_node_id, destination_node_id, travel_time_min 
                FROM fact_time_matrix 
                WHERE time_window = '{time_window_scenario}';
            """
            df_time = conn.execute(time_query).df()
            
            # 2. Build index representations
            customers = df_cust["customer_id"].tolist()
            nodes = [0] + customers  # Injecting Depot (0) as the initial root node
            vehicles = df_veh["vehicle_id"].tolist()
            
            # 3. Build algebraic parameters mapping (Simulating constraints for optimization testing)
            # Default operational constraints: 15-min delivery dwell, 150kg uniform demand
            demands = {c: 150.0 for c in customers}
            demands[0] = 0.0  # Depot demand is zero
            
            capacities = dict(zip(df_veh["vehicle_id"], df_veh["capacity_kg"]))
            
            service_times = {n: 15.0 for n in nodes}
            service_times[0] = 0.0  # No service time at departure depot
            
            # Formulating strict delivery windows (e_i = 8 AM (480 min), l_i = 1 PM (780 min), l_i= 6pm (1080 min))
            earliest_times = {n: 480.0 for n in nodes}
            latest_times = {n: 1080.0 for n in nodes}
            
            # Absolute bounds for the depot operating shift (6 AM to 10 PM)
            earliest_times[0] = 360.0
            latest_times[0] = 1320.0
            
            # Build the cost matrix mapping t_ij
            travel_times = {}
            for _, row in df_time.iterrows():
                o = int(row["origin_node_id"])
                d = int(row["destination_node_id"])
                travel_times[(o, d)] = float(row["travel_time_min"])
                
            return cls(nodes, customers, vehicles, demands, capacities, 
                       service_times, earliest_times, latest_times, travel_times)
                       
        finally:
            conn.close()