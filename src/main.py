# main.py
"""
Master Orchestration Script - Logística Bogotá Express
Epic: epic:devops-automation
Task: Task 09: Orchestrate End-to-End Execution Pipeline

Centralized workflow orchestrator that invokes your real decoupled 
system components sequentially using exact Python file modules.
"""

import os
import sys
import time

try:
    from data_generator import BogotaDataGenerator                        # source: 1
    from data_ingestion import BogotaDataIngestion                        # source: 2
    from database_manager import LogisticsDatabaseManager                  # source: 3
    from distance_matrix import HaversineDistanceMatrixCalculator        # source: 4
    from traffic_engine import TrafficSimulationEngine                    # source: 5
    from vrptw_data_model import VRPTWDataModel                          # source: 6
    from vrptw_data_solver import MIPRouteSolver                          # source: 7
    
except ImportError as e:
    print(f"\n[CRITICAL ERROR] some script was not founded: {e}")

    sys.exit(1)

def run_pipeline():
    print("=" * 75)
    print("   LAUNCHING LOGÍSTICA BOGOTÁ EXPRESS AUTOMATED END-TO-END PIPELINE   ")
    print("=" * 75)
    start_time = time.time()
    
    RAW_DIR = "data/raw"
    DB_PATH = os.path.join("data/processed", "logistic_warehouse.db")
    
    # -------------------------------------------------------------------------
    # STAGE 1: Data Engineering - Generation & Ingestion (Task 04)
    # -------------------------------------------------------------------------
    print("\n[STAGE 1/4] Running Data Ingestion and Database Schema Initialization...")
    
    db_manager = LogisticsDatabaseManager(db_filename="logistic_warehouse.db")
    db_manager.connect()
    db_manager.initialize_schema()
    db_manager.close()
    
    generator = BogotaDataGenerator(num_customers=60, output_dir=RAW_DIR)
    generator.run_pipeline()
    
    # 1.3 Ingestar datos hacia las tablas limpias de DuckDB (data_ingestion.py)
    ingestion = BogotaDataIngestion(db_path=DB_PATH, raw_dir=RAW_DIR)
    ingestion.run_pipeline()
    
    # -------------------------------------------------------------------------
    # STAGE 2: Spatial Analytics - Distance Matrix Generation (Task 05)
    # -------------------------------------------------------------------------
    print("\n[STAGE 2/4] Computing Vectorized Georeferenced Haversine Matrix...")
    # Ejecuta el cálculo matricial desde distance_matrix.py
    distance_calc = HaversineDistanceMatrixCalculator(db_path=DB_PATH)
    distance_calc.execute_pipeline()
    
    # -------------------------------------------------------------------------
    # STAGE 3: Temporal Simulation - Traffic Friction Engine (Task 06)
    # -------------------------------------------------------------------------
    print("\n[STAGE 3/4] Simulating Time-Dependent Traffic Network Coefficients...")
    # Simula las penalizaciones por trancón desde traffic_engine.py
    traffic_sim = TrafficSimulationEngine(db_path=DB_PATH)
    traffic_sim.execute_pipeline()
    
    # -------------------------------------------------------------------------
    # STAGE 4: Prescriptive Optimization - MILP Mathematical Engine (Task 08)
    # -------------------------------------------------------------------------
    print("\n[STAGE 4/4] Activating Prescriptive Optimization Solver Engine...")
    try:
        # Cargar los conjuntos y parámetros desde vrptw_data_model.py
        data_container = VRPTWDataModel.from_warehouse(db_path=DB_PATH, time_window_scenario="rush_hour")
        
        # Construir y resolver el modelo matemático usando vrptw_data_solver.py
        solver_engine = MIPRouteSolver(data=data_container)
        solver_engine.build_decision_variables()
        solver_engine.build_objective_function()
        solver_engine.build_constraints()
        
        # Ejecutar la búsqueda de rutas óptimas
        solver_engine.solve(time_limit_sec=25)
        print("-> Operations Research mathematical solver complete.")
        
    except Exception as e:
        print(f"[ERROR] Optimization routine collapsed: {e}")
        sys.exit(1)
        
    # -------------------------------------------------------------------------
    # METRICAS DE FINALIZACIÓN
    # -------------------------------------------------------------------------
    total_time = time.time() - start_time
    print("\n" + "=" * 75)
    print("PIPELINE AUTOMATION SUMMARY: SUCCESSFUL")
    print(f"Total Operational Execution Runtime: {total_time:.2f} seconds")
    print("=" * 75)

if __name__ == "__main__":
    run_pipeline()