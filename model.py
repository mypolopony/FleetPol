import random
import math
from mesa import Model
from mesa.space import ContinuousSpace
from mesa.agent import AgentSet
from agents import Truck
from environment import Location

class FleetModel(Model):
    """
    The main model for the fleet simulation.
    Manages trucks (agents) and locations.
    """
    # Default space for visualization components that might access it at class level
    space = ContinuousSpace(x_max=50, y_max=50, torus=False)

    def __init__(self, num_trucks=10, num_depots=2, num_customers=20, map_width=50, map_height=50, seed=None):
        super().__init__(seed=seed)

        self.num_trucks = num_trucks
        self.random = random.Random(seed)
        self._current_agent_id = 0

        # New spatial grid setup for visualization
        # self.space = ContinuousSpace(map_width, map_height, torus=False)

        # AgentSet is used to manage trucks
        # The second argument should be the random.Random instance for AgentSet's internal shuffling.
        self.fleet_agents = AgentSet([], self.random)
        self.schedule = self.fleet_agents

        # Create locations
        self.locations = []
        for i in range(num_depots):
            loc = Location(
                unique_id=self.next_id(),
                name=f"Depot-{chr(65 + i)}",
                loc_type="depot",
                lat=self.random.uniform(0, map_height),
                lon=self.random.uniform(0, map_width),
                resources={"loading_docks": self.random.randint(1, 5),
                           "fuel_liters": self.random.randint(20000, 50000),
                           "widgets": self.random.randint(500, 2000)}, # Initial stock of widgets
                production_details={"resource_name": "widgets",
                                    "rate_per_step": self.random.randint(50, 150), # Depots produce widgets
                                    "capacity": self.random.randint(5000, 10000)},
                model=self
            )
            self.locations.append(loc)

        for i in range(num_customers):
            loc = Location(
                unique_id=self.next_id(),
                name=f"Customer-{i+1:03d}",
                loc_type="customer",
                lat=self.random.uniform(0, map_height),
                lon=self.random.uniform(0, map_width),
                resources={}, # Customers start with no resources
                model=self
            )
            self.locations.append(loc)
            # Add initial demands to customers
            if loc.type == "customer":
                num_initial_demands = self.random.randint(0, 3) # Each customer can start with 0 to 3 demands
                for _ in range(num_initial_demands):
                    loc.add_demand(self.steps, "widgets", self.random.randint(10, 100))


        # Create trucks
        for i in range(num_trucks):
            start_depot = self.random.choice([loc for loc in self.locations if loc.type == "depot"])
            truck_agent = Truck(
                unique_id=self.next_id(),
                descriptive_id=f"TRK-{i+1:03d}",
                start_location=start_depot,
                model=self,
                capacity_kg=self.random.randint(15, 30) * 1000 # Added capacity_kg
            )
            self.fleet_agents.add(truck_agent)
            # Place truck on space
            self.space.place_agent(truck_agent, (start_depot.longitude, start_depot.latitude))
            self.schedule.add(truck_agent)
            truck_agent.pos = (start_depot.longitude, start_depot.latitude)

    def next_id(self):
        self._current_agent_id += 1
        return self._current_agent_id

    def step(self):
        # --- Location Production Step ---
        for loc in self.locations:
            if hasattr(loc, 'step_produce'):
                loc.step_produce()

        # --- Agent (Truck) Step ---
        self.fleet_agents.shuffle_do("step") # Calls step() on each truck
        
        # --- Demand Generation Step ---
        # Periodically add new demands to customers
        if self.random.random() < 0.1: # 10% chance each step to add a new demand somewhere
            customer_locs = [loc for loc in self.locations if loc.type == "customer"]
            if customer_locs:
                chosen_customer = self.random.choice(customer_locs)
                chosen_customer.add_demand(self.steps, "widgets", self.random.randint(20,150))
                # print(f"[{self.steps}] New demand added at {chosen_customer.name}")

        # --- Route Assignment Step ---
        # Assign new routes to idle trucks at depots, prioritizing customers with demands
        for agent in self.fleet_agents:
            if isinstance(agent, Truck) and agent.status == "idle_at_depot" and not agent.route:
                # 30% chance to try to get a new route
                if self.random.random() < 0.3:
                    # Find customers with pending demands for "widgets" (or other producible goods)
                    customers_with_demands = []
                    for loc in self.locations:
                        if loc.type == "customer" and hasattr(loc, 'demands'):
                            if any(d['status'] in ['pending', 'partially_fulfilled'] and d['resource_name'] == "widgets" for d in loc.demands):
                                customers_with_demands.append(loc)
                    
                    route_plan = []
                    if not customers_with_demands:
                        # If no customers have demands for widgets, maybe a random exploratory route or stay put
                        # For now, let's try a random customer if any exist for other potential goods (not yet modeled)
                        # Or simply don't assign a route if no specific demand to target.
                        # For simplicity, if no widget demands, truck stays idle unless we add other logic.
                        pass # Truck remains idle or could get a generic route
                    else:
                        # Prioritize customers with demands for widgets
                        num_stops = self.random.randint(1, min(3, len(customers_with_demands)))
                        route_plan = self.random.sample(customers_with_demands, num_stops)

                    if not route_plan:
                        continue # No route determined for this truck this step

                    depots = [loc for loc in self.locations if loc.type == "depot"]
                    if depots:
                        route_plan.append(self.random.choice(depots)) # End route at a depot
                    else:
                        # If no depots, truck can't return. This is a modeling issue.
                        # For now, if no depots, don't assign this route.
                        continue
                    
                    agent.assign_route(route_plan)
                    # Optional: print(f"[{self.steps}] Assigned new route to {agent.descriptive_id}: {[loc.name for loc in route_plan]}")
