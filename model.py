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
        self.space = ContinuousSpace(map_width, map_height, torus=False)

        # AgentSet is used to manage trucks
        # The second argument should be the random.Random instance for AgentSet's internal shuffling.
        self.fleet_agents = AgentSet([], self.random)

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

    def next_id(self):
        self._current_agent_id += 1
        return self._current_agent_id

    def step(self):
        self.fleet_agents.shuffle_do("step")
