"""
Defines the Mesa Model for the Fleet POL Simulator.
"""
import mesa
import random

from agents import Truck
from environment import Location # Assuming Location remains a non-agent class for now

class FleetModel(mesa.Model):
    """
    The main model for the fleet simulation.
    Manages trucks (agents) and locations.
    """
    def __init__(self, num_trucks=10, num_depots=2, num_customers=20, map_width=50, map_height=50, seed=None):
        """
        Initialize the FleetModel.

        Args:
            num_trucks (int): Number of trucks to create.
            num_depots (int): Number of depots to create.
            num_customers (int): Number of customer locations to create.
            map_width (int): Width of the simulated area (for generating locations).
            map_height (int): Height of the simulated area.
        """
        super().__init__() # Call base __init__ without seed first
        self.num_trucks = num_trucks
        self._current_agent_id = 0 # Manual ID counter
        # Explicitly initialize self.random for the model instance
        self.random = random.Random(seed)
        # In Mesa 3, AgentSet replaces traditional schedulers for many use cases.
        # Agents are added to this set, and then operations like shuffle_do are called.
        # The first argument is the initial list of agents, the second is the model.
        self.fleet_agents = AgentSet([], self) # Renamed from self.agents
        self.running = True # For conditional stopping via DataCollector or other means

        self.locations = {} # Store Location objects, keyed by name or ID
        self.map_width = map_width
        self.map_height = map_height

        # Create Locations
        self._create_locations(num_depots, num_customers)

        # Create Truck Agents
        # Ensure depots exist before creating trucks that start at depots
        depot_locations = [loc for loc in self.locations.values() if loc.location_type == "depot"]
        if not depot_locations:
            raise ValueError("No depots created. Trucks need a starting depot.")

        for i in range(self.num_trucks):
            truck_id_str = f"TRK-{str(i+1).zfill(3)}"
            start_depot = self.random.choice(depot_locations)
            # Mesa agent unique_id is an int, truck_id_str is for description
            truck_agent = Truck(unique_id=self._get_next_agent_id(), # Using manual ID generation
                                model=self,
                                descriptive_id=truck_id_str,
                                start_location=start_depot,
                                capacity_kg=self.random.randint(15, 30) * 1000)
            self.fleet_agents.add(truck_agent) # Renamed from self.agents
            # print(f"Created: {truck_agent} at {start_depot.name}")


        # Optional: DataCollector for collecting agent/model data
        self.datacollector = mesa.DataCollector(
            model_reporters={"TotalCargo": lambda m: sum(a.current_cargo_kg for a in m.fleet_agents if isinstance(a, Truck))}, # Renamed from m.agents
            agent_reporters={"Status": "status", "Location": lambda a: a.current_location.name, "Cargo": "current_cargo_kg"}
        )
