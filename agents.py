"""
Defines the agents for the Fleet POL Simulator, compatible with Mesa.
"""
from typing import Dict, Optional, Any
from mesa import Agent, Model
from environment import Location

class Truck(Agent):
    """
    Represents a truck in the fleet, as a Mesa Agent.
    """
    def __init__(self, 
                 unique_id: int,
                 model: Model,
                 descriptive_id: str,
                 start_location: Location,
                 capacity_kg: int = 150) -> None:
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
        self.cargo_manifest = {} # item_name: quantity for specific cargo items
        self.unloading_in_progress = False
    
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

    def _log_event(self,
                   event_type: str,
                   details: Dict[str, Any]) -> None:
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

    def _perform_move(self, 
                      destination_location: Location) -> None:
        """Internal helper to manage location changes and logging.
        
        Args:
            destination_location (Location): The target location to move to."""
        if destination_location:
            self.pos = (destination_location.longitude, destination_location.latitude)
        else:
            # If no destination specified, log and return
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
            self.model.space.move_agent(self, (destination_location.longitude, destination_location.latitude))
        
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


    def load_cargo(self, 
                   resource_name: str,
                   quantity: int,
                   weight_per_unit_kg: float = 1.0) -> bool:
        """ Loads a specific type of cargo onto the truck. 
        
        Args:
            resource_name (str): The name of the resource to load (e.g., "widgets").
            quantity (int): The number of units to load.
            weight_per_unit_kg (float): The weight of each unit in kilograms. Default is 1kg.
        Returns:
            bool: True if loading was successful, False otherwise.
        """
        if self.status not in ["idle_at_depot", "loading_at_depot", "pending_load_for_route"]: # Trucks load at depots
             self._log_event("load_cargo_failed", {"resource_name": resource_name, "quantity": quantity, "reason": f"invalid_status_{self.status}"})
             return False

        amount_kg = quantity * weight_per_unit_kg
        if self.current_cargo_kg + amount_kg <= self.capacity_kg:
            self.current_cargo_kg += amount_kg
            self.cargo_manifest[resource_name] = self.cargo_manifest.get(resource_name, 0) + quantity
            self._log_event("load_cargo", {
                "resource_name": resource_name,
                "quantity_loaded": quantity,
                "weight_loaded_kg": amount_kg,
                "current_cargo_kg": self.current_cargo_kg,
                "current_manifest": self.cargo_manifest.copy(),
                "location_name": str(self.current_location.name)
            })
            # Attempt to consume from location (depot)
            if hasattr(self.current_location, 'consume_resource'):
                if not self.current_location.consume_resource(self.model.steps, resource_name, quantity, truck_id=self.descriptive_id):
                    # Rollback if location doesn't have the resource
                    self.current_cargo_kg -= amount_kg
                    self.cargo_manifest[resource_name] -= quantity
                    if self.cargo_manifest[resource_name] == 0:
                        del self.cargo_manifest[resource_name]
                    self._log_event("load_cargo_failed", {"resource_name": resource_name, "quantity": quantity, "reason": "source_location_insufficient_resource"})
                    return False
            return True
        self._log_event("load_cargo_failed", {
            "resource_name": resource_name,
            "quantity_requested": quantity,
            "weight_requested_kg": amount_kg,
            "reason": "exceeds_capacity",
            "location_name": str(self.current_location.name)
        })
        return False

    def unload_cargo(self, resource_name, quantity_to_unload, weight_per_unit_kg=1): # Added resource_name and weight
        """ Unloads a specific type of cargo from the truck. """
        if self.status not in ["idle_at_customer", "unloading_at_customer"]: # Trucks unload at customers
            self._log_event("unload_cargo_failed", {"resource_name": resource_name, "quantity": quantity_to_unload, "reason": f"invalid_status_{self.status}"})
            return False

        if self.cargo_manifest.get(resource_name, 0) >= quantity_to_unload:
            amount_kg_to_unload = quantity_to_unload * weight_per_unit_kg
            self.current_cargo_kg -= amount_kg_to_unload
            self.cargo_manifest[resource_name] -= quantity_to_unload
            if self.cargo_manifest[resource_name] == 0:
                del self.cargo_manifest[resource_name]

            # Attempt to fulfill demand at the customer location
            fulfilled_at_loc = 0
            if hasattr(self.current_location, 'fulfill_demand'):
                fulfilled_at_loc = self.current_location.fulfill_demand(self.model.steps, resource_name, quantity_to_unload, truck_id=self.descriptive_id)
            
            # Even if not all was used by demand, log it as unloaded from truck
            self._log_event("unload_cargo", {
                "resource_name": resource_name,
                "quantity_unloaded": quantity_to_unload,
                "weight_unloaded_kg": amount_kg_to_unload,
                "current_cargo_kg": self.current_cargo_kg,
                "current_manifest": self.cargo_manifest.copy(),
                "location_name": str(self.current_location.name),
                "fulfilled_at_location": fulfilled_at_loc
            })
            # If location couldn't take it (e.g. no demand), it's still off the truck.
            # More complex logic could have truck take it back or try other demands.
            return True

        self._log_event("unload_cargo_failed", {
            "resource_name": resource_name,
            "quantity_requested_to_unload": quantity_to_unload,
            "reason": "insufficient_cargo_on_truck",
            "current_manifest": self.cargo_manifest.copy(),
            "location_name": str(self.current_location.name)
        })
        return False

    def set_status(self, 
                   new_status: str, 
                   details=None):
        """ Sets the truck's status and logs it.
         
        Args:
            new_status (str): The new status to set (e.g., "idle_at_depot", "en_route").
            details (dict, optional): Additional details to log with the status change.
        """
        old_status = self.status
        self.status = new_status
        log_details = {"old_status": old_status, "new_status": new_status,
                       "location_name": str(self.current_location.name)}
        if details:
            log_details.update(details)
        self._log_event("status_change", log_details)

    def assign_route(self, 
                     route_locations: list[Location]) -> None:
        """ Assigns a route (list of Location objects) to the truck. """
        self.route = list(route_locations) # Ensure it's a mutable copy
        self._log_event("route_assigned", {
            "route_names": [str(loc.name) for loc in route_locations],
            "num_stops": len(route_locations)
        })
        if self.route and self.status == "idle_at_depot":
            # If idle at depot and gets a route, prepare to load
            self.set_status("pending_load_for_route", {"route_assigned": [str(loc.name) for loc in self.route]})
        elif self.route and self.status == "idle_at_customer":
            # If at customer and gets a new route (e.g., to return to depot or another customer), prepare to depart
            self.set_status(f"pending_departure_to_{self.route[0].name}")
        elif self.route and self.status == "idle_at_other": # Or any other idle state where it might get a route
             self.set_status(f"pending_departure_to_{self.route[0].name}")


    def step(self):
        """
        Defines the agent's behavior at each step of the simulation.
        """
        if self.status == "en_route":
            # If it was 'en_route', it means it "arrived" in this step (simplified).
            # The 'arrive' event was logged by _perform_move. Now set status based on location type.
            if self.current_location.type == "depot":
                self.set_status("idle_at_depot")
            elif self.current_location.type == "customer":
                self.set_status("idle_at_customer")
            else:
                self.set_status("idle_at_other")
            # print(f"[{self.model.steps}] {self.descriptive_id} completed move, now {self.status} at {self.current_location.name}")


        elif self.status == "pending_load_for_route":
            # This truck is at a depot and has been assigned a route. Try to load cargo.
            resource_to_load = "widgets" # Example: always try to load widgets if on route
            loaded_this_step = False

            if self.current_location.type == "depot" and self.current_cargo_kg < self.capacity_kg:
                if self.current_location.resources.get(resource_to_load, 0) > 0:
                    max_qty_to_load_by_weight = int((self.capacity_kg - self.current_cargo_kg) / 1) # Assuming 1kg/unit for widgets
                    qty_at_depot = self.current_location.resources.get(resource_to_load, 0)
                    
                    target_cargo_kg = self.capacity_kg * 0.75 # Target 75% capacity
                    needed_kg = target_cargo_kg - self.current_cargo_kg
                    
                    if needed_kg > 0:
                        target_load_qty = int(needed_kg / 1) # Assuming 1kg/unit for widgets
                        amount_to_load_qty = min(target_load_qty, qty_at_depot, max_qty_to_load_by_weight)
                        amount_to_load_qty = max(0, amount_to_load_qty)

                        if amount_to_load_qty > 0:
                            if self.load_cargo(resource_to_load, amount_to_load_qty, weight_per_unit_kg=1):
                                loaded_this_step = True
                                # Stay in "pending_load_for_route" if not yet full and depot might have more,
                                # or transition to "loading_at_depot" as an intermediate if multi-step loading was complex.
                                # For now, let's assume it will re-evaluate in next step if still pending_load_for_route.
                                # If it's now "full enough", it will transition out below.
                                self.set_status("loading_at_depot", {"reason": "load_successful_eval_next_step"}) # Mark as actively loading this step
                            else:
                                # Loading failed (e.g. depot ran out mid-attempt)
                                self.set_status(f"pending_departure_to_{self.route[0].name}" if self.route else "idle_at_depot", {"reason": "load_attempt_failed_in_pending_load"})
                            return # End step, loading action (success or fail) takes time.
            
            # After attempting to load (or if conditions weren't met for an attempt):
            # Check if "full enough" or if depot is out of the resource.
            is_full_enough = self.current_cargo_kg >= int(self.capacity_kg) * 0.75
            depot_has_resource = self.current_location.type == "depot" and self.current_location.resources.get(resource_to_load, 0) > 0
            
            if not loaded_this_step and (is_full_enough or not depot_has_resource or self.current_location.type != "depot"):
                # Transition to pending departure if route exists and loading is considered done/not possible.
                if self.route:
                    self.set_status(f"pending_departure_to_{self.route[0].name}", {"reason": "loading_phase_complete_or_cannot_load"})
                else:
                    self.set_status("idle_at_depot", {"reason": "no_route_after_pending_load_evaluation"})
            elif not loaded_this_step: # Did not load, but not full and depot has resource - implies it should try again
                 self.set_status("pending_load_for_route", {"reason": "re_evaluating_load"}) # Stay to try again next step
            # If loaded_this_step was true, we already returned.

        elif self.status == "loading_at_depot":
            # This status indicates a successful load_cargo call happened in the *same step* from "pending_load_for_route".
            # Now, decide if more loading is needed or if it's time to depart.
            is_full_enough = self.current_cargo_kg >= int(self.capacity_kg * 0.75)
            depot_has_resource = self.current_location.resources.get("widgets", 0) > 0 # Assuming widgets

            if is_full_enough or not depot_has_resource:
                if self.route:
                    self.set_status(f"pending_departure_to_{self.route[0].name}", {"reason": "loading_complete_ready_for_departure"})
                else:
                    self.set_status("idle_at_depot", {"reason": "loading_complete_but_no_route"})
            else:
                # Not full enough and depot has resources, try to load more next step.
                self.set_status("pending_load_for_route", {"reason": "continuing_load_attempt_from_loading_status"})

        elif self.route and self.status not in ["en_route", "pending_load_for_route", "loading_at_depot"]:
            # This covers "idle_at_customer",  "pending_departure_to_...", or finished loading
            # Also "idle_at_other" if it has a route.

            # Try to unload as much as we can
            if self.status == "idle_at_customer" and self.current_cargo_kg > 0:
                if hasattr(self.current_location, 'demands'):
                    for demand in self.current_location.demands:
                        if demand["status"] in ["pending", "partially_fulfilled"] and \
                           demand["resource_name"] in self.cargo_manifest and \
                           self.cargo_manifest[demand["resource_name"]] > 0:
                            
                            qty_on_truck = self.cargo_manifest[demand["resource_name"]]
                            qty_needed_for_demand = demand["quantity_requested"] - demand["quantity_fulfilled"]
                            amount_to_unload_qty = min(qty_on_truck, qty_needed_for_demand)

                            if amount_to_unload_qty > 0:
                                self.set_status("unloading_at_customer")
                                self.unload_cargo(demand["resource_name"], amount_to_unload_qty, weight_per_unit_kg=1)
                                demand["quantity_fulfilled"] += amount_to_unload_qty
                                # Check if demand is fully satisfied
                                if demand["quantity_fulfilled"] >= demand["quantity_requested"]:
                                    demand["status"] = "fulfilled"
                                    # Log the fulfillment event
                                    self._log_event("demand_fulfilled", {
                                        "resource_name": demand["resource_name"],
                                        "quantity_fulfilled": amount_to_unload_qty,
                                        "customer_name": str(self.current_location.name),
                                        "demand_id": demand.get("id", "unknown")
                                    })
                                else:
                                    demand["status"] = "partially_fulfilled"

                                # Log the unload event
                                self._log_event("unload_cargo", {
                                    "resource_name": demand["resource_name"],
                                    "quantity_unloaded": amount_to_unload_qty,
                                    "weight_unloaded_kg": amount_to_unload_qty * 1, # Assuming 1kg/unit for widgets
                                    "current_cargo_kg": self.current_cargo_kg,
                                    "current_manifest": self.cargo_manifest.copy(),
                                    "location_name": str(self.current_location.name)
                                })
                    self.status = "finished_unloading" # Set status to indicate unloading is done
                    return

            if self.status.startswith("pending_departure_to_") or \
               (self.status == "finished_unloading" and self.route) or \
               (self.status == "idle_at_other" and self.route):

                if not self.route:
                    current_loc_type = self.current_location.type if self.current_location else "unknown"
                    self.set_status("idle_at_depot" if current_loc_type == "depot" else "idle_at_location", {"reason":"no_route_before_departure"})
                    return
                
                actual_destination = self.route.pop(0)
                # print(f"[{self.model.steps}] {self.descriptive_id} starting move from {self.current_location.name} to {actual_destination.name}")
                self._perform_move(actual_destination)
                # Status becomes 'en_route' due to _perform_move

        elif not self.route and self.status not in ["en_route", "idle_at_depot"]:
            # No route, try to return to a depot if not already there
            # This is a very simple "return home" logic
            if self.current_location.type != "depot":
                depots = [loc for loc_id, loc in self.model.locations.items() if loc.type == "depot"]
                if depots:
                    # print(f"[{self.model.steps}] {self.descriptive_id} has no route, returning to depot.")
                    self.assign_route([self.model.random.choice(depots)]) # Go to a random depot
                    # The next step() call will handle the movement if status allows

        # else:
            # print(f"[{self.model.steps}] {self.descriptive_id} is {self.status} at {self.current_location.name}, no action this step.")