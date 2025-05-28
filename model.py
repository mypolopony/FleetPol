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
                resources={"loading_docks": self.random.randint(1, 5), "fuel_liters": self.random.randint(20000, 50000)},
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
                resources={},
                model=self
            )
            self.locations.append(loc)

        # Create trucks
        for i in range(num_trucks):
            start_depot = self.random.choice([loc for loc in self.locations if loc.type == "depot"])
            truck_agent = Truck(
                unique_id=self.next_id(),
                descriptive_id=f"TRK-{i+1:03d}", # Changed 'name' to 'descriptive_id'
                start_location=start_depot, # Changed 'current_location' to 'start_location'
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
        self.fleet_agents.shuffle_do("step")
        # Assign new routes to idle trucks at depots
        for agent in self.fleet_agents:
            if isinstance(agent, Truck) and agent.status == "idle_at_depot" and not agent.route:
                # 30% chance to get a new random route
                if self.random.random() < 0.3: 
                    num_stops = self.random.randint(1, 3)
                    
                    customer_locations = [loc for loc in self.locations if loc.type == "customer"]
                    if not customer_locations:
                        continue # Skip if no customers to assign

                    # Ensure we don't try to pick more stops than available customers
                    actual_num_stops = min(num_stops, len(customer_locations))
                    if actual_num_stops == 0:
                        continue

                    route_plan = self.random.sample(customer_locations, actual_num_stops)
                    
                    depots = [loc for loc in self.locations if loc.type == "depot"]
                    if depots:
                        route_plan.append(self.random.choice(depots))
                    else:
                        # If there are no depots, this truck can't complete a typical cycle.
                        # For now, if no depots, don't assign this route.
                        continue
                    
                    agent.assign_route(route_plan)
                    # Optional: print(f"[{self.steps}] Assigned new route to {agent.descriptive_id}: {[loc.name for loc in route_plan]}")
