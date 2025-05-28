"""
Defines the environment components for the Fleet POL Simulator,
such as locations, routes, and the world itself.
"""

class Location:
    """
    Represents a physical location in the simulation.
    """
    def __init__(self, name, latitude, longitude, location_type="generic"):
        """
        Initializes a Location.

        Args:
            name (str): Human-readable name of the location (e.g., "Warehouse A", "Customer X").
            latitude (float): Latitude coordinate.
            longitude (float): Longitude coordinate.
            location_type (str): Type of location (e.g., "depot", "customer", "fuel_station", "rest_area").
        """
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.location_type = location_type
        self.resources = {}  # e.g., {"fuel": 10000, "loading_docks": 5}
        self.current_trucks = []  # List of truck_ids currently at this location
        self.event_log = [] # List of (sim_time, event_type, details)
        self._log_event(0, "location_created", {"name": self.name, "type": self.location_type, "lat": self.latitude, "lon": self.longitude}) # Assuming sim_time starts at 0

    def __str__(self):
        return f"Location({self.name}, Type: {self.location_type}, Lat: {self.latitude}, Lon: {self.longitude})"

    def __repr__(self):
        return f"Location(name='{self.name}', lat={self.latitude}, lon={self.longitude}, type='{self.location_type}')"

    def _log_event(self, sim_time, event_type, details):
        """
        Logs an event for this location.
        Args:
            sim_time (float/int): The current simulation time.
            event_type (str): The type of event.
            details (dict): A dictionary containing event-specific information.
        """
        self.event_log.append((sim_time, event_type, details))

    def add_resource(self, sim_time, resource_name, quantity):
        """Adds a resource or updates its quantity at the location."""
        old_quantity = self.resources.get(resource_name, 0)
        self.resources[resource_name] = old_quantity + quantity
        self._log_event(sim_time, "resource_added", {
            "resource_name": resource_name,
            "quantity_added": quantity,
            "new_total": self.resources[resource_name]
        })

    def consume_resource(self, sim_time, resource_name, quantity, truck_id=None):
        """Consumes a resource from the location if available."""
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

    def truck_arrived(self, sim_time, truck_id):
        """Records a truck arriving at this location."""
        if truck_id not in self.current_trucks:
            self.current_trucks.append(truck_id)
            self._log_event(sim_time, "truck_arrived", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})
        else:
            # Log if truck is already marked as present, could indicate an issue or re-arrival
            self._log_event(sim_time, "truck_already_present", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})


    def truck_departed(self, sim_time, truck_id):
        """Records a truck departing from this location."""
        if truck_id in self.current_trucks:
            self.current_trucks.remove(truck_id)
            self._log_event(sim_time, "truck_departed", {"truck_id": truck_id, "current_truck_count": len(self.current_trucks)})
        else:
            # Log if truck is not found, could indicate an issue
            self._log_event(sim_time, "truck_not_found_on_departure", {"truck_id": truck_id})


# Example Usage (will be integrated into the main simulation)
if __name__ == '__main__':
    sim_clock = 0
    depot = Location("Central Depot", 34.0522, -118.2437, "depot") # Logs creation at sim_clock 0
    sim_clock +=1
    depot.add_resource(sim_clock, "loading_docks", 10)
    sim_clock +=1
    depot.add_resource(sim_clock, "fuel", 50000) # Liters
    print(depot)
    print(f"[{sim_clock}] Resources at {depot.name}: {depot.resources}")

    sim_clock +=1
    customer_site = Location("Customer MegaCorp", 34.0600, -118.2500, "customer")
    print(customer_site)

    # Simulating resource consumption
    sim_clock +=1
    if depot.consume_resource(sim_clock, "fuel", 100, truck_id="TRK-TEST-01"):
        print(f"[{sim_clock}] Consumed 100L fuel from {depot.name}. Remaining: {depot.resources['fuel']}L")
    else:
        print(f"[{sim_clock}] Failed to consume fuel from {depot.name}.")

    sim_clock +=1
    depot.truck_arrived(sim_clock, "TRK-TEST-01")
    print(f"[{sim_clock}] Trucks at {depot.name}: {depot.current_trucks}")
    sim_clock +=1
    depot.truck_departed(sim_clock, "TRK-TEST-01")
    print(f"[{sim_clock}] Trucks at {depot.name}: {depot.current_trucks}")

    print(f"\n--- {depot.name} Event Log ---")
    for event in depot.event_log:
        print(event)
    
    print(f"\n--- {customer_site.name} Event Log ---")
    for event in customer_site.event_log:
        print(event)