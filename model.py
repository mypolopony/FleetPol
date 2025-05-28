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
        depot_locations = [loc for loc in self.locations.values() if loc.type == "depot"]
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
        # Using _get_next_agent_id for location unique IDs as well, ensuring they are unique across all entities.
        # Alternatively, a separate counter for locations could be used if IDs only need to be unique among locations.
        for i in range(num_depots):
            name = f"Depot-{chr(65+i)}"
            lat = round(self.random.uniform(0, self.map_height), 4)
            lon = round(self.random.uniform(0, self.map_width), 4)
            depot = Location(
                unique_id=self._get_next_agent_id(), # Provide unique_id
                name=name,
                latitude=lat, # Ensure 'lat' and 'lon' match Location.__init__
                longitude=lon,
                loc_type="depot",
                model=self, # Provide model reference
                resources={"loading_docks": self.random.randint(1, 5),
                           "fuel_liters": self.random.randint(20000, 50000),
                           "widgets": self.random.randint(500, 2000)},
                production_details={"resource_name": "widgets",
                                    "rate_per_step": self.random.randint(50, 150),
                                    "capacity": self.random.randint(5000, 10000)}
            )
            self.locations[name] = depot # Storing by name, could also store in a list or by ID

        for i in range(num_customers):
            name = f"Customer-{str(i+1).zfill(3)}"
            lat = round(self.random.uniform(0, self.map_height), 4)
            lon = round(self.random.uniform(0, self.map_width), 4)
            customer = Location(
                unique_id=self._get_next_agent_id(), # Provide unique_id
                name=name,
                latitude=lat, # Ensure 'lat' and 'lon' match Location.__init__
                longitude=lon,
                loc_type="customer", # Ensure 'loc_type' matches Location.__init__
                model=self, # Provide model reference
                resources={} # Customers start with no resources
            )
            self.locations[name] = customer
            # Add initial demands to customers
            num_initial_demands = self.random.randint(0, 3)
            for _ in range(num_initial_demands):
                # self.steps is 0 here, which is fine for initial demand creation time
                customer.add_demand(self.steps, "widgets", self.random.randint(10, 100))
        
        # Initial resource logging for depots was moved into their creation loop.
        # The production details are also set during creation.
        # The old loop for adding resources to depots is no longer needed here as it's handled above.


    def step(self) -> None:
        """
        Advance the model by one step.
        Order of operations: Collect data, produce resources, agents act, generate new demands, assign routes.
        """
        self.datacollector.collect(self)

        # --- Location Production Step ---
        for loc_obj in self.locations.values(): # Iterate through location objects
            if hasattr(loc_obj, 'step_produce'):
                loc_obj.step_produce()

        # --- Agent (Truck) Step ---
        self.fleet_agents.shuffle_do("step")

        # --- Demand Generation Step ---
        if self.random.random() < 0.1: # 10% chance each step to add a new demand
            customer_locs = [loc for loc in self.locations.values() if loc.type == "customer"]
            if customer_locs:
                chosen_customer = self.random.choice(customer_locs)
                chosen_customer.add_demand(self.steps, "widgets", self.random.randint(20, 150))

        # --- Route Assignment Step ---
        for agent in self.fleet_agents:
            if isinstance(agent, Truck) and agent.status == "idle_at_depot" and not agent.route:
                if self.random.random() < 0.3: # 30% chance to try to get a new route
                    customers_with_demands = [
                        loc for loc in self.locations.values()
                        if loc.type == "customer" and hasattr(loc, 'demands') and
                           any(d['status'] in ['pending', 'partially_fulfilled'] and d['resource_name'] == "widgets" for d in loc.demands)
                    ]
                    
                    route_plan = []
                    if customers_with_demands:
                        num_stops = self.random.randint(1, min(3, len(customers_with_demands)))
                        route_plan = self.random.sample(customers_with_demands, num_stops)
                    # else: No specific "widget" demands, truck might stay idle or get a generic route (not implemented yet)

                    if route_plan: # Only assign if a route was actually planned
                        depots = [loc for loc in self.locations.values() if loc.type == "depot"]
                        if depots:
                            route_plan.append(self.random.choice(depots)) # End route at a depot
                            agent.assign_route(route_plan)
                            # print(f"[{self.steps}] Assigned new route to {agent.descriptive_id}: {[loc.name for loc in route_plan]}")
                        # Else: no depots to return to, problematic. Route not assigned.