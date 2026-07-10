import pulp
import os
from vrptw_data_model import VRPTWDataModel

class MIPRouteSolver:
    """
    Mixed-Integer Linear Programming Engine to resolve the VRPTW equations
    using the pre-computed spatiotemporal data structures.
    """
    def __init__(self, data: VRPTWDataModel):
        self.data = data
        
        # 1. Initialize the Optimization Problem Instance (Cost Minimization)
        self.prob = pulp.LpProblem("Logistica_Bogota_Express_VRPTW", pulp.LpMinimize)
        
        # Big-M value definition (Safe maximum tracking horizon)
        self.big_M = 100000.0
        
        # Placeholders for variables
        self.x = {}
        self.w = {}

    def build_decision_variables(self):
        """
        Step 1: Declares decision variables inside the solver workspace.
        """
        # Binary variables x_ijk
        for k in self.data.vehicles:
            for i in self.data.nodes:
                for j in self.data.nodes:
                    if i != j:
                        self.x[(i, j, k)] = pulp.LpVariable(
                            name=f"x_{i}_{j}_{k}", 
                            cat=pulp.LpBinary
                        )
                        
        # Continuous temporal arrival variables w_ik
        for k in self.data.vehicles:
            for i in self.data.nodes:
                self.w[(i, k)] = pulp.LpVariable(
                    name=f"w_{i}_{k}", 
                    lowBound=self.data.earliest_times[i], 
                    upBound=self.data.latest_times[i], 
                    cat=pulp.LpContinuous
                )

    def build_objective_function(self):
        """
        Step 2: Maps the cost minimization objective based on dynamic travel times.
        """
        self.prob += pulp.lpSum(
            self.data.travel_times[(i, j)] * self.x[(i, j, k)]
            for k in self.data.vehicles
            for i in self.data.nodes
            for j in self.data.nodes
            if i != j
        ), "Global_Transit_Time_Minimization"

    def solve(self, time_limit_sec: int = 60):
        """
        Step 3: Configuration and execution of the algebraic solver.
        """
        print(f"[SOLVER ENGINE] Invoking CBC Branch-and-Bound solver. Time ceiling: {time_limit_sec}s")
        
        # Configure execution parameters (Thread usage and hard time cutoffs)
        solver = pulp.PULP_CBC_CMD(
            msg=True, 
            timeLimit=time_limit_sec, 
            threads=4
        )
        
        # Trigger optimization search
        self.prob.solve(solver)
        
        print(f"[SOLVER ENGINE] Optimization routine finished. Status: {pulp.LpStatus[self.prob.status]}")


if __name__ == "__main__":
    # Execution Test Harness
    DB_PATH = os.path.join("data/processed", "logistic_warehouse.db")
    
    # 1. Hydrate the Data Model container from DuckDB
    data_container = VRPTWDataModel.from_warehouse(db_path=DB_PATH, time_window_scenario="rush_hour")
    
    # 2. Build and solve the operational formulation
    solver_engine = MIPRouteSolver(data=data_container)
    solver_engine.build_decision_variables()
    solver_engine.build_objective_function()
    
    # Let's run a test setup verification
    print(f"[PIPELINE VALIDATION] Data Model structured successfully. Active stores: {len(data_container.customers)}")