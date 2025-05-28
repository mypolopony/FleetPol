"""
Defines the environment components for the Fleet POL Simulator,
such as locations, routes, and the world itself.
"""

import mesa
from typing import Dict, Optional, Any

class Location:
    """
    Represents a physical location in the simulation.
    """
    def __init__(self, 
                 unique_id: int, 
                 name: str, 
                 latitude: float, 
                 longitude: float, 
                 loc_type:str, 
                 model:mesa.Model, 
                 resources: Optional[dict[str, Any]], 
                 production_details=None) -> None:
        """
        Initializes a Location.

        Args:
            unique_id (int): Unique identifier for the location.
            name (str): Human-readable name of the location.
            lat (float): Latitude coordinate.
            lon (float): Longitude coordinate.
            loc_type (str): Type of location (e.g., "depot", "customer", "factory").
            model (mesa.Model): The model instance this location belongs to.
            resources (dict, optional): Initial resources. Defaults to None.
            production_details (dict, optional): Details for resource production.
                                                 e.g., {"resource_name": "widgets", "rate_per_step": 5, "capacity": 1000}
        """
        self.unique_id = unique_id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.type = loc_type
        self.model = model
        self.resources = resources if resources is not None else {}
        self.current_trucks = []  # List of truck_ids currently at this location
        self.event_log = [] # List of (sim_time, event_type, details)
        self.demands = [] # List of demand dicts: {"demand_id": unique_id, "resource_name": str, "quantity": int, "status": "pending/fulfilled"}
        self.production_details = production_details if production_details is not None else {}
        
        # Log creation event using model's current time if available
        sim_time = self.model.steps if hasattr(self.model, 'steps') else 0
        log_create_details = {
            "name": self.name, "type": self.type,
            "lat": self.latitude, "lon": self.longitude, "id": self.unique_id
        }
        if self.production_details:
            log_create_details["production"] = self.production_details
        self._log_event(sim_time, "location_created", log_create_details)

    def __str__(self):
        return f"Location({self.name}, Type: {self.type}, Lat: {self.latitude}, Lon: {self.longitude}, Demands: {len(self.demands)})"

    def __repr__(self):
        return f"Location(name='{self.name}', lat={self.latitude}, lon={self.longitude}, type='{self.type}')"

    def _log_event(self, 
                   sim_time: float | int, 
                   event_type: str, 
                   details: Dict[str, Any]):
        """
        Logs an event for this location.
        Args:
            sim_time (float/int): The current simulation time.
            event_type (str): The type of event.
            details (dict): A dictionary containing event-specific information.
        """
        self.event_log.append((sim_time, event_type, details))

    def add_resource(self, 
                     sim_time: float | int, 
                     resource_name: str, 
                     quantity: int) -> None:
        """Adds a resource or updates its quantity at the location.
        
        Args:
            sim_time (float | int): The current simulation time.
            resource_name (str): The name of the resource to add.
            quantity (int): The amount of the resource to add.
        """
        old_quantity = self.resources.get(resource_name, 0)
        self.resources[resource_name] = old_quantity + quantity
        self._log_event(sim_time, "resource_added", {
            "resource_name": resource_name,
            "quantity_added": quantity,
            "new_total": self.resources[resource_name]
        })

    def consume_resource(self,
                         sim_time: float | int, 
                         resource_name: str, 
                         quantity: int, 
                         truck_id=Optional[str]) -> bool:
        """Consumes a resource from the location if available.
        
        Args:
            sim_time (float | int): The current simulation time.
            resource_name (str): The name of the resource to consume.
            quantity (int): The amount of the resource to consume.
            truck_id (str, optional): ID of the truck consuming the resource, if applicable.
        """
        if self.resources.get(resource_name, 0) >= quantity:
            self.resources[resource_name] -= quantity
            log_details = {
                "resource_name": resource_name,
                "quantity_consumed": quantity,
                "remaining_total": self.resources[resource_name]
            }
            if truck_id:
                log_details["truck_id"] = truck_id
            self._log_event(sim_time, "resource_consumed", log_details)
            return True
        log_details_fail = {
            "resource_name": resource_name,
            "quantity_requested": quantity,
            "reason": "insufficient_resource"
        }
        if truck_id:
            log_details_fail["truck_id"] = truck_id
        self._log_event(sim_time, "resource_consumption_failed", log_details_fail)
        return False

    def truck_arrived(self, 
                      sim_time: float | int, 
                      truck_id: str) -> None:
        """Records a truck arriving at this location.
        
        Args:
            sim_time (float | int): The current simulation time.
            truck_id (str): Unique identifier for the truck arriving.
        """
        if truck_id not in self.current_trucks:
            self.current_trucks.append(truck_id)
            self._log_event(sim_time, "truck_arrived", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})
        else:
            # Log if truck is already marked as present, could indicate an issue or re-arrival
            self._log_event(sim_time, "truck_already_present", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})


    def truck_departed(self, 
                       sim_time: float | int, 
                       truck_id: str) -> None:
        """Records a truck departing from this location.
        
        Args:
            sim_time (float | int): The current simulation time.
            truck_id (str): Unique identifier for the truck departing.
        """
        if truck_id in self.current_trucks:
            self.current_trucks.remove(truck_id)
            self._log_event(sim_time, "truck_departed", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})
        else:
            # Log if truck is not found, could indicate an issue
            self._log_event(sim_time, "truck_not_found_on_departure", {"truck_id": truck_id})

    def step_produce(self) -> None:
        """Produces resources based on production_details if applicable."""
        if not self.production_details or "resource_name" not in self.production_details or "rate_per_step" not in self.production_details:
            return

        resource_name = self.production_details["resource_name"]
        rate = self.production_details["rate_per_step"]
        capacity = self.production_details.get("capacity", float('inf')) # Optional production capacity

        current_amount = self.resources.get(resource_name, 0)
        if current_amount < capacity:
            amount_to_produce = min(rate, capacity - current_amount)
            if amount_to_produce > 0:
                self.add_resource(self.model.steps, resource_name, amount_to_produce)
                # No separate log for "production" event, add_resource already logs "resource_added"
                # Could add a specific "production_event" if needed for finer-grained tracking.
                # For now, "resource_added" with context of production_details should suffice.

    def add_demand(self, 
                   sim_time: float | int,
                   resource_name: str,
                   quantity: int,
                   demand_id: Optional[str] = None) -> str:
        """Adds a new demand to the location.
        
        Args:
            sim_time (float | int): The current simulation time.
            resource_name (str): The name of the resource for which demand is being added.
            quantity (int): The quantity of the resource requested.
            demand_id (str, optional): Unique identifier for the demand. If None, a simple unique ID will be generated.
        Returns:
            str: The unique ID of the created demand.
        """
        if self.type != "customer":
            self._log_event(sim_time, "add_demand_failed", {"reason": "not_customer_location", "resource": resource_name, "quantity": quantity})
            return None

        if demand_id is None:
            # Create a simple unique ID for the demand within this location
            demand_id = f"demand_{self.name}_{len(self.demands)}_{self.model.random.randint(1000,9999)}"

        new_demand = {
            "demand_id": demand_id,
            "resource_name": resource_name,
            "quantity_requested": quantity,
            "quantity_fulfilled": 0,
            "status": "pending", # "pending", "partially_fulfilled", "fulfilled"
            "created_at_step": sim_time
        }
        self.demands.append(new_demand)
        self._log_event(sim_time, "demand_added", {
            "demand_id": new_demand["demand_id"],
            "resource_name": resource_name,
            "quantity": quantity,
            "location_name": self.name
        })
        return new_demand["demand_id"]

    def fulfill_demand(self, 
                       sim_time: str | int,
                       resource_name: str,
                       quantity_delivered: int, 
                       truck_id: Optional[str] = None) -> int:
        """Attempts to fulfill pending demands for a given resource.

        Args:
            sim_time (float | int): The current simulation time.
            resource_name (str): The name of the resource being delivered.
            quantity_delivered (int): The amount of resource delivered.
            truck_id (str, optional): ID of the truck delivering the resource, if applicable.
        Returns:
            int: The total quantity fulfilled from this delivery.
        """
        if self.type != "customer":
            return 0 # Only customers have demands to fulfill

        fulfilled_this_delivery = 0
        for demand in self.demands:
            if demand["status"] in ["pending", "partially_fulfilled"] and \
               demand["resource_name"] == resource_name and \
               quantity_delivered > 0:

                can_fulfill_for_this_demand = demand["quantity_requested"] - demand["quantity_fulfilled"]
                amount_to_fulfill = min(quantity_delivered, can_fulfill_for_this_demand)

                demand["quantity_fulfilled"] += amount_to_fulfill
                quantity_delivered -= amount_to_fulfill
                fulfilled_this_delivery += amount_to_fulfill

                old_status = demand["status"]
                if demand["quantity_fulfilled"] >= demand["quantity_requested"]:
                    demand["status"] = "fulfilled"
                else:
                    demand["status"] = "partially_fulfilled"

                log_details = {
                    "demand_id": demand["demand_id"],
                    "resource_name": resource_name,
                    "quantity_delivered_for_demand": amount_to_fulfill,
                    "total_fulfilled_for_demand": demand["quantity_fulfilled"],
                    "demand_status_before": old_status,
                    "demand_status_after": demand["status"],
                    "location_name": self.name
                }
                if truck_id:
                    log_details["truck_id"] = truck_id
                self._log_event(sim_time, "demand_updated", log_details)

                if quantity_delivered == 0:
                    break # No more quantity from this delivery to distribute
        
        if fulfilled_this_delivery > 0:
             self._log_event(sim_time, "demand_fulfillment_processed", {
                "resource_name": resource_name,
                "total_delivered_for_resource": fulfilled_this_delivery,
                "remaining_delivery_unallocated": quantity_delivered,
                "location_name": self.name,
                "truck_id": truck_id
            })
        return fulfilled_this_delivery


# Example Usage (will be integrated into the main simulation)
if __name__ == '__main__':
    # Mock model for standalone testing
    class MockModel:
        def __init__(self):
            self.steps = 0
            import random
            self.random = random.Random(12345) # For predictable demand_ids if needed

    mock_model = MockModel()
    sim_clock = 0 # Use model steps

    depot = Location(unique_id=1, name="Central Depot", latitude=34.0522, longitude=-118.2437, loc_type="depot", model=mock_model)
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    depot.add_resource(sim_clock, "loading_docks", 10)
    sim_clock +=1
    depot.add_resource(sim_clock, "fuel", 50000) # Liters
    print(depot)
    print(f"[{sim_clock}] Resources at {depot.name}: {depot.resources}")

    mock_model.steps +=1 ; sim_clock = mock_model.steps
    customer_site = Location(unique_id=2, name="Customer MegaCorp", latitude=34.0600, longitude=-118.2500, loc_type="customer", model=mock_model)
    print(customer_site)

    mock_model.steps +=1 ; sim_clock = mock_model.steps
    demand_id_1 = customer_site.add_demand(sim_clock, "widgets", 100)
    print(f"[{sim_clock}] Added demand {demand_id_1} for 100 widgets at {customer_site.name}")
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    demand_id_2 = customer_site.add_demand(sim_clock, "gadgets", 50)
    print(f"[{sim_clock}] Added demand {demand_id_2} for 50 gadgets at {customer_site.name}")
    print(f"[{sim_clock}] Demands at {customer_site.name}: {customer_site.demands}")


    # Simulating resource consumption (at depot)
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    if depot.consume_resource(sim_clock, "fuel", 100, truck_id="TRK-TEST-01"):
        print(f"[{sim_clock}] Consumed 100L fuel from {depot.name}. Remaining: {depot.resources['fuel']}L")
    else:
        print(f"[{sim_clock}] Failed to consume fuel from {depot.name}.")

    # Simulating truck arrival/departure (at depot)
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    depot.truck_arrived(sim_clock, "TRK-TEST-01")
    print(f"[{sim_clock}] Trucks at {depot.name}: {depot.current_trucks}")
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    depot.truck_departed(sim_clock, "TRK-TEST-01")
    print(f"[{sim_clock}] Trucks at {depot.name}: {depot.current_trucks}")

    # Simulating demand fulfillment (at customer)
    mock_model.steps +=1 ; sim_clock = mock_model.steps
    print(f"[{sim_clock}] Before fulfillment at {customer_site.name}: {customer_site.demands[0]}")
    fulfilled_amount = customer_site.fulfill_demand(sim_clock, "widgets", 70, truck_id="TRK-TEST-01")
    print(f"[{sim_clock}] Delivered 70 widgets to {customer_site.name}. Fulfilled: {fulfilled_amount}. Demand status: {customer_site.demands[0]['status']}")
    print(f"[{sim_clock}] After partial fulfillment: {customer_site.demands[0]}")

    mock_model.steps +=1 ; sim_clock = mock_model.steps
    fulfilled_amount_2 = customer_site.fulfill_demand(sim_clock, "widgets", 40, truck_id="TRK-TEST-01") # Deliver more
    print(f"[{sim_clock}] Delivered 40 more widgets to {customer_site.name}. Fulfilled: {fulfilled_amount_2}. Demand status: {customer_site.demands[0]['status']}")
    print(f"[{sim_clock}] After full fulfillment: {customer_site.demands[0]}")


    print(f"\n--- {depot.name} Event Log ---")
    for event in depot.event_log:
        print(event)
    
    print(f"\n--- {customer_site.name} Event Log ---")
    for event in customer_site.event_log:
        print(event)