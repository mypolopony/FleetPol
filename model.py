"""
Defines the Mesa Model for the Fleet POL Simulator.
"""
import mesa
from mesa.agent import AgentSet
import random

from agents import Truck
from environment import Location # Assuming Location remains a non-agent class for now

class FleetModel(mesa.Model):
    """
    The main model for the fleet simulation.
    Manages trucks (agents) and locations.
    """
    def __init__(self, num_trucks: int=10, num_depots: int=2, num_customers: int=20, map_width: int=50, map_height: int=50, seed=None) -> None:
        """
        Initialize the FleetModel.

        Args:
            num_trucks (int): Number of trucks to create.
            num_depots (int): Number of depots to create.
            num_customers (int): Number of customer locations to create.
            map_width (int): Width of the simulated area (for generating locations).
            map_height (int): Height of the simulated area.
        """
        super().__init__(seed=seed) # Pass seed to base Model class
        self.num_trucks = num_trucks
        self._current_agent_id = 0 # Manual ID counter
        
        # In Mesa 3, AgentSet replaces traditional schedulers for many use cases.
        # Agents are added to this set, and then operations like shuffle_do are called.
        # The first argument is the initial list of agents, the second is the model.
        self.fleet_agents = AgentSet([], self) 
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
            self.fleet_agents.add(truck_agent)
            # print(f"Created: {truck_agent} at {start_depot.name}")

        # Optional: DataCollector for collecting agent/model data
        self.datacollector = mesa.DataCollector(
            model_reporters={"TotalCargo": lambda m: sum(a.current_cargo_kg for a in m.fleet_agents if isinstance(a, Truck))}, # Renamed from m.agents
            agent_reporters={"Status": "status", "Location": lambda a: a.current_location.name, "Cargo": "current_cargo_kg"}
        )

    def _get_next_agent_id(self) -> int:
        """Generates a new unique ID for an agent."""
        self._current_agent_id += 1
        return self._current_agent_id

    def _create_locations(self, num_depots: int, num_customers: int) -> None:
        """Helper method to create and store locations."""
        loc_id_counter = 0
        for i in range(num_depots):
            loc_id_counter += 1
            name = f"Depot-{chr(65+i)}" # Depot-A, Depot-B
            lat = round(self.random.uniform(0, self.map_height), 4)
            lon = round(self.random.uniform(0, self.map_width), 4)
            depot = Location(name=name, latitude=lat, longitude=lon, location_type="depot")
            # Pass self.steps if Location's __init__ or _log_event expects it from model
            # For now, Location logs its own creation time as 0 or relies on explicit time passing.
            # depot._log_event(self.steps, "location_created_by_model", {"details": "..."})
            self.locations[name] = depot
            # print(f"Created location: {depot}")

        for i in range(num_customers):
            loc_id_counter += 1
            name = f"Customer-{str(i+1).zfill(3)}"
            lat = round(self.random.uniform(0, self.map_height), 4)
            lon = round(self.random.uniform(0, self.map_width), 4)
            customer = Location(name=name, latitude=lat, longitude=lon, location_type="customer")
            self.locations[name] = customer
            # print(f"Created location: {customer}")
        
        # Add some resources to depots
        for loc_name, loc_obj in self.locations.items():
            if loc_obj.location_type == "depot":
                # self.steps is 0 during __init__, which is fine for initial resource logging.
                loc_obj.add_resource(self.steps, "loading_docks", self.random.randint(2,5))
                loc_obj.add_resource(self.steps, "fuel_liters", self.random.randint(20000, 50000))


    def step(self) -> None:
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self) # Collect data at the beginning of the step
        self.fleet_agents.shuffle_do("step") # Mesa v3: AgentSet calls agent's 'step' method. Renamed from self.agents
        # print(f"--- Model step {self.steps} complete. Time: {self.steps} ---")

        # Simple logic for trucks to get new routes if idle at depot
        for agent in self.fleet_agents: # Iterate over AgentSet. Renamed from self.agents
            if isinstance(agent, Truck) and agent.status == "idle_at_depot" and not agent.route:
                if self.random.random() < 0.3: # 30% chance to get a new random route
                    num_stops = self.random.randint(1, 3)
                    route_plan = [self.random.choice(list(self.locations.values())) for _ in range(num_stops)]
                    # Ensure the route ends back at a depot (can be the same or different)
                    depots = [loc for loc_name, loc in self.locations.items() if loc.location_type == "depot"]
                    if depots:
                        route_plan.append(self.random.choice(depots))
                    
                    agent.assign_route(route_plan)
                    # print(f"[{self.steps}] Assigned new route to {agent.descriptive_id}: {[loc.name for loc in route_plan]}")