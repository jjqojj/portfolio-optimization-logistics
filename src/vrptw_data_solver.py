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
        
    def build_constraints(self):
        """
        Step 3: Translates the structural MILP equations into the solver workspace.
        """
        print("[SOLVER ENGINE] Injecting operational constraints into workspace...")

        # 1. Single-Service Visit Guarantee
        # Para cada cliente, la suma de visitas de todos los camiones debe ser exactamente 1
        for i in self.data.customers:
            self.prob += pulp.lpSum(
                self.x[(i, j, k)] 
                for k in self.data.vehicles 
                for j in self.data.nodes 
                if i != j
            ) == 1, f"Single_Visit_Guarantee_Store_{i}"

        # 2. Conservation of Flow (Nodal Equilibrium)
        # Lo que entra a un cliente por un camión 'k', debe salir por el mismo camión
        for k in self.data.vehicles:
            for m in self.data.customers:
                self.prob += pulp.lpSum(self.x[(i, m, k)] for i in self.data.nodes if i != m) == \
                             pulp.lpSum(self.x[(m, j, k)] for j in self.data.nodes if m != j), \
                             f"Flow_Conservation_Vehicle_{k}_Node_{m}"

        # 3. Depot Continuity (Departure & Return)
        # Cada camión puede salir del CEDI máximo 1 vez y regresar máximo 1 vez
        for k in self.data.vehicles:
            self.prob += pulp.lpSum(self.x[(0, j, k)] for j in self.data.customers) <= 1, f"Depot_Departure_Vehicle_{k}"
            self.prob += pulp.lpSum(self.x[(i, 0, k)] for i in self.data.customers) <= 1, f"Depot_Return_Vehicle_{k}"

        # 4. Vehicle Payload Capacity Constraints
        # La carga total asignada a un camión 'k' no puede superar su capacidad máxima Q_k
        for k in self.data.vehicles:
            self.prob += pulp.lpSum(
                self.data.demands[i] * pulp.lpSum(self.x[(i, j, k)] for j in self.data.nodes if i != j)
                for i in self.data.customers
            ) <= self.data.capacities[k], f"Payload_Capacity_Vehicle_{k}"

        # 5. Temporal Continuity and Subtour Elimination (Big-M Technique)
        # w_ik + s_i + t_ij - w_jk <= M * (1 - x_ijk)
        for k in self.data.vehicles:
            for i in self.data.nodes:
                for j in self.data.nodes:
                    if i != j:
                        self.prob += (
                            self.w[(i, k)] + self.data.service_times[i] + self.data.travel_times[(i, j)] 
                            - self.w[(j, k)] <= self.big_M * (1 - self.x[(i, j, k)])
                        ), f"Time_Continuity_BigM_{i}_{j}_{k}"

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
    
    # 2. Build objective function and decision variables
    solver_engine = MIPRouteSolver(data=data_container)
    solver_engine.build_decision_variables()
    solver_engine.build_objective_function()
    
    # 3. Build restrictitions
    solver_engine.build_constraints()

    # 4. Solve
    solver_engine.solve(time_limit_sec=30)
    
    # Let's run a test setup verification
    print(f"[PIPELINE VALIDATION] Data Model structured successfully. Active stores: {len(data_container.customers)}")