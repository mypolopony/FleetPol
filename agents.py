"""
Defines the agents for the Fleet POL Simulator, compatible with Mesa.
"""
from mesa import Agent
# import random # No longer needed globally here, model will provide its own random instance

class Truck(Agent):
    """
    Represents a truck in the fleet, as a Mesa Agent.
    """
    def __init__(self, unique_id, model, descriptive_id, start_location, capacity_kg=20000):
        """
        Initializes a Truck agent.

        Args:
            unique_id (int): Mesa's unique identifier for the agent.
            model (mesa.Model): The model instance the agent belongs to.
            descriptive_id (str): A human-readable identifier for the truck (e.g., "TRK-001").
            start_location (Location): The initial location object of the truck.
            capacity_kg (int): Maximum cargo capacity in kilograms.
        """
        # In Mesa v3, Agent.__init__ requires 'model' but not 'unique_id'.
        # 'unique_id' is set when the agent is added to an AgentSet.
        self.unique_id = unique_id # Store unique_id as it's passed in
        self.model = model # Store model as it's passed in
        super().__init__(model=self.model) # Pass model to super
        self.descriptive_id = descriptive_id
        self.current_location = start_location # This is a Location object
        self.capacity_kg = capacity_kg
        self.current_cargo_kg = 0
        self.status = "idle_at_depot"
        self.route = []  # List of Location objects
        self.history = [] # List of (sim_time, event_type, details)

        # Log creation event using model's current time
        self._log_event("truck_created", {
            "descriptive_id": self.descriptive_id,
            "start_location_name": str(self.current_location.name), # Log name for readability
            "capacity_kg": self.capacity_kg
        })
        # Inform the starting location that the truck has "arrived" there
        if self.current_location and hasattr(self.current_location, 'truck_arrived'):
            self.current_location.truck_arrived(self.model.steps, self.descriptive_id)


    def __str__(self):
        return (f"Truck({self.descriptive_id}, MesaID: {self.unique_id}, "
                f"Loc: {str(self.current_location.name)}, Status: {self.status}, "
                f"Cargo: {self.current_cargo_kg}kg)")

    def _log_event(self, event_type, details):
        """
        Logs an event for this truck using the model's current simulation time.
        Args:
            event_type (str): The type of event (e.g., "move", "load_cargo").
            details (dict): A dictionary containing event-specific information.
        """
        # Ensure details always includes truck_id for easier filtering later
        log_entry_details = {"truck_id": self.descriptive_id}
        log_entry_details.update(details)
        self.history.append((self.model.steps, event_type, log_entry_details))

    def _perform_move(self, destination_location):
        """Internal helper to manage location changes and logging."""
        if not destination_location:
            self._log_event("move_failed", {"reason": "no_destination_specified"})
            return

        from_location_obj = self.current_location
        
        self._log_event("depart", {
            "from_location_name": str(from_location_obj.name),
            "to_location_name": str(destination_location.name)
        })
        if hasattr(from_location_obj, 'truck_departed'):
            from_location_obj.truck_departed(self.model.steps, self.descriptive_id) # Changed to model.steps

        self.current_location = destination_location
        # Update agent's position in the ContinuousSpace
        if hasattr(self.model, 'space') and self.model.space is not None:
            self.model.space.move_agent(self, (destination_location.lon, destination_location.lat))
        
        self.status = "en_route" # Status becomes en_route upon departure

        # Simulate arrival at the next step or after some delay in a more complex model
        # For now, we'll assume arrival is processed in the same step or by agent's step logic
        # The 'arrive' event should ideally be logged when the truck actually reaches.
        # Let's make the step() method handle arrival.
        # self.status = "arrived_at_destination" # This will be set in step() after "movement"
        if hasattr(destination_location, 'truck_arrived'):
            destination_location.truck_arrived(self.model.steps, self.descriptive_id) # Changed to model.steps
        
        self._log_event("arrive", { # Simplified: log arrival immediately after departure for now
            "location_name": str(self.current_location.name)
        })


    def load_cargo(self, amount_kg):
        """ Loads cargo onto the truck. """
        if self.status not in ["idle_at_depot", "loading_at_depot", "idle_at_customer"]: # Simplified valid states
             self._log_event("load_cargo_failed", {"amount_kg": amount_kg, "reason": f"invalid_status_{self.status}"})
             return False
        if self.current_cargo_kg + amount_kg <= self.capacity_kg:
            self.current_cargo_kg += amount_kg
            self._log_event("load_cargo", {
                "amount_kg": amount_kg, "current_cargo_kg": self.current_cargo_kg,
                "location_name": str(self.current_location.name)
            })
            return True
        self._log_event("load_cargo_failed", {
            "amount_kg": amount_kg, "reason": "exceeds_capacity",
            "location_name": str(self.current_location.name)
        })
        return False

    def unload_cargo(self, amount_kg):
        """ Unloads cargo from the truck. """
        if self.status not in ["idle_at_customer", "unloading_at_customer"]: # Simplified valid states
            self._log_event("unload_cargo_failed", {"amount_kg": amount_kg, "reason": f"invalid_status_{self.status}"})
            return False
        if self.current_cargo_kg - amount_kg >= 0:
            self.current_cargo_kg -= amount_kg
            self._log_event("unload_cargo", {
                "amount_kg": amount_kg, "current_cargo_kg": self.current_cargo_kg,
                "location_name": str(self.current_location.name)
            })
            return True
        self._log_event("unload_cargo_failed", {
            "amount_kg": amount_kg, "reason": "insufficient_cargo",
            "location_name": str(self.current_location.name)
        })
        return False

    def set_status(self, new_status, details=None):
        """ Sets the truck's status and logs it. """
        old_status = self.status
        self.status = new_status
        log_details = {"old_status": old_status, "new_status": new_status,
                       "location_name": str(self.current_location.name)}
        if details:
            log_details.update(details)
        self._log_event("status_change", log_details)

    def assign_route(self, route_locations):
        """ Assigns a route (list of Location objects) to the truck. """
        self.route = list(route_locations) # Ensure it's a mutable copy
        self._log_event("route_assigned", {
            "route_names": [str(loc.name) for loc in route_locations],
            "num_stops": len(route_locations)
        })
        if self.route and self.status in ["idle_at_depot", "idle_at_customer"]: # Start moving if idle and has a route
            self.set_status(f"pending_departure_to_{self.route[0].name}")


    def step(self):
        """
        Defines the agent's behavior at each step of the simulation.
        """
        
        # Simple behavior: if on a route and not currently 'en_route', try to move to the next location.
        # If 'en_route', it means it departed in a previous part of this step or a previous step.
        # For simplicity, let's assume movement takes one step.
        # A more complex model would handle travel time over multiple steps.

        if self.status == "en_route":
            # If it was 'en_route', it means it "arrived" in this step (simplified).
            # The 'arrive' event was logged by _perform_move. Now set status based on location type.
            if self.current_location.location_type == "depot":
                self.set_status("idle_at_depot")
            elif self.current_location.location_type == "customer":
                self.set_status("idle_at_customer")
            else:
                self.set_status("idle_at_other")
            # print(f"[{self.model.steps}] {self.descriptive_id} completed move, now {self.status} at {self.current_location.name}")


        elif self.route and self.status not in ["en_route", "loading_at_depot", "unloading_at_customer"]: # Can start moving
            next_destination = self.route[0] # Peek at next destination
            
            # Basic decision: if at depot and has cargo space, try to load (example)
            if self.status == "idle_at_depot" and self.current_cargo_kg < self.capacity_kg / 2:
                 # Try to load some cargo if at depot and not full
                if self.model.random.random() < 0.5: # 50% chance to try loading
                    amount_to_load = self.model.random.randint(1000, int(self.capacity_kg / 4))
                    self.set_status("loading_at_depot")
                    self.load_cargo(amount_to_load)
                    # print(f"[{self.model.steps}] {self.descriptive_id} attempting to load at {self.current_location.name}")
                    return # End step here, loading takes time

            # Basic decision: if at customer and has cargo, try to unload
            elif self.status == "idle_at_customer" and self.current_cargo_kg > 0:
                if self.model.random.random() < 0.7: # 70% chance to try unloading
                    amount_to_unload = self.model.random.randint(1000, self.current_cargo_kg)
                    self.set_status("unloading_at_customer")
                    self.unload_cargo(amount_to_unload)
                    # print(f"[{self.model.steps}] {self.descriptive_id} attempting to unload at {self.current_location.name}")
                    return # End step here, unloading takes time

            # If no loading/unloading action, or if ready to move:
            if self.status not in ["loading_at_depot", "unloading_at_customer"]:
                actual_destination = self.route.pop(0) # Consume the destination from route
                # print(f"[{self.model.steps}] {self.descriptive_id} starting move from {self.current_location.name} to {actual_destination.name}")
                self._perform_move(actual_destination)
                # Status becomes 'en_route' due to _perform_move

        elif not self.route and self.status not in ["en_route", "idle_at_depot"]:
            # No route, try to return to a depot if not already there
            # This is a very simple "return home" logic
            if self.current_location.location_type != "depot":
                depots = [loc for loc_id, loc in self.model.locations.items() if loc.location_type == "depot"]
                if depots:
                    # print(f"[{self.model.steps}] {self.descriptive_id} has no route, returning to depot.")
                    self.assign_route([self.model.random.choice(depots)]) # Go to a random depot
                    # The next step() call will handle the movement if status allows

        # else:
            # print(f"[{self.model.steps}] {self.descriptive_id} is {self.status} at {self.current_location.name}, no action this step.")


# The __main__ block is for standalone testing and will not be used by Mesa.
# It needs significant updates to work with the new Agent structure (requires a mock Model).
# For now, we'll rely on testing within the Mesa model.
if __name__ == '__main__':
    print("This script defines the Truck Agent for Mesa. Run it via a Mesa model.")
    # To test standalone, you'd need to mock a Mesa model and scheduler:
    # class MockModel:
    #     def __init__(self):
    #         self.schedule = MockScheduler()
    #         self.locations = {} # Mock locations
    # class MockScheduler:
    #     def __init__(self):
    #         self.time = 0
    #
    # # Mock Location for agent testing
    # class MockLocationForAgentTest:
    #     def __init__(self, name, location_type="generic"):
    #         self.name = name
    #         self.location_type = location_type
    #     def __str__(self): return self.name
    #     def truck_arrived(self, sim_time, truck_id): print(f"Mock: {truck_id} arrived at {self.name} at {sim_time}")
    #     def truck_departed(self, sim_time, truck_id): print(f"Mock: {truck_id} departed {self.name} at {sim_time}")

    # model = MockModel()
    # depot = MockLocationForAgentTest("Depot Alpha", "depot")
    # customer = MockLocationForAgentTest("Customer Beta", "customer")
    # model.locations = {"depot_alpha": depot, "customer_beta": customer}
    #
    # truck1 = Truck(unique_id=1, model=model, descriptive_id="TRK-007", start_location=depot, capacity_kg=10000)
    # print(truck1)
    #
    # model.schedule.time = 1
    # truck1.assign_route([customer, depot])
    #
    # model.schedule.time = 2
    # truck1.step() # Should try to move
    # print(truck1)
    #
    # model.schedule.time = 3
    # truck1.step() # Should be 'idle_at_customer'
    # print(truck1)
    #
    # print("\n--- Truck 1 History ---")
    # for event in truck1.history:
    #     print(event)