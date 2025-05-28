"""
Main script for running the Fleet POL Simulator using Mesa.
"""
from model import FleetModel
from agents import Truck # To check instance type for logging

def run_mesa_simulation(num_trucks=20, num_depots=3, num_customers=30, num_steps=50):
    """
    Initializes and runs the Mesa-based fleet simulation.

    Args:
        num_trucks (int): Number of trucks to simulate.
        num_depots (int): Number of depots.
        num_customers (int): Number of customer locations.
        num_steps (int): Number of steps to run the simulation for.
    """
    print(f"Initializing Mesa Fleet POL Simulator with {num_trucks} trucks, "
          f"{num_depots} depots, {num_customers} customers for {num_steps} steps...")

    # Create the model
    model = FleetModel(num_trucks=num_trucks, num_depots=num_depots, num_customers=num_customers)

    print("\n--- Initial Model Setup ---")
    print(f"Number of agents created: {len(model.fleet_agents)}")
    print(f"Number of locations created: {len(model.locations)}")
    
    # Optionally print initial details of a few trucks/locations
    print("\nSample Initial Trucks:")
    for i, agent in enumerate(model.fleet_agents):
        if i < 3 and isinstance(agent, Truck): # Print first 3 trucks
            print(agent)
        elif i >=3:
            break
            
    print("\nSample Initial Locations:")
    for i, (loc_name, loc_obj) in enumerate(model.locations.items()): # Unpack key and value
        if i < 100: # Print first few
            print(f"Name: {loc_name}, Details: {loc_obj}") # loc_obj will use Location.__str__
            if hasattr(loc_obj, 'resources') and loc_obj.resources:
                print(f"  Resources: {loc_obj.resources}")
            if hasattr(loc_obj, 'production_details') and loc_obj.production_details:
                print(f"  Production: {loc_obj.production_details}")
            if hasattr(loc_obj, 'demands') and loc_obj.demands:
                print(f"  Demands: {loc_obj.demands}")
        else:
            break

    # Run the simulation
    print(f"\n--- Running simulation for {num_steps} steps ---")
    for i in range(num_steps):
        model.step()
        if (i + 1) % 10 == 0: # Print a message every 10 steps
            print(f"Completed step {i + 1}/{num_steps} (Time: {model.steps})")

    print(f"\n--- Simulation Complete after {num_steps} steps ---")

    # Display logs for a sample truck and a sample location
    if model.fleet_agents:
        # Find the first Truck agent to display its log
        sample_truck_agent = next((agent for agent in model.fleet_agents if isinstance(agent, Truck)), None)
        if sample_truck_agent:
            print(f"\n--- Event Log for Truck {sample_truck_agent.descriptive_id} (Mesa ID: {sample_truck_agent.unique_id}) ---")
            for event_time, event_type, event_details in sample_truck_agent.history:
                log_line = f"Time: {event_time}, Type: {event_type}"
                if event_type == "load_cargo":
                    log_line += f", Resource: {event_details.get('resource_name')}, Qty Loaded: {event_details.get('quantity_loaded')}"
                elif event_type == "unload_cargo":
                    log_line += f", Resource: {event_details.get('resource_name')}, Qty Unloaded: {event_details.get('quantity_unloaded')}"
                # Optionally, add more specific parsing for other event types or just print full details
                log_line += f", Details: {event_details}"
                print(log_line)
        else:
            print("\nNo Truck agents found to display history.")
    else:
        print("\nNo agents in the simulation to display history.")

    # This block should be inside the function, using the 'model' instance
    if model.locations: # model.locations is now a list
        # Print logs for a sample depot and a sample customer if they exist
        # model.locations is a dictionary, so we iterate through its values (Location objects)
        sample_depot = next((loc_obj for loc_obj in model.locations.values() if loc_obj.type == "depot"), None)
        sample_customer = next((loc_obj for loc_obj in model.locations.values() if loc_obj.type == "customer"), None)

        if sample_depot:
            print(f"\n--- Event Log for Depot {sample_depot.name} ---")
            for event_time, event_type, event_details in sample_depot.event_log:
                log_line = f"Time: {event_time}, Type: {event_type}"
                if event_type == "resource_consumed":
                    log_line += f", Resource: {event_details.get('resource_name')}, Qty Consumed: {event_details.get('quantity_consumed')}, By: {event_details.get('truck_id')}"
                elif event_type == "resource_added": # From production
                     log_line += f", Resource: {event_details.get('resource_name')}, Qty Added: {event_details.get('quantity_added')}"
                log_line += f", Details: {event_details}"
                print(log_line)
        
        if sample_customer:
            print(f"\n--- Event Log for Customer {sample_customer.name} ---")
            for event_time, event_type, event_details in sample_customer.event_log:
                log_line = f"Time: {event_time}, Type: {event_type}"
                if event_type == "demand_added":
                    log_line += f", Resource: {event_details.get('resource_name')}, Qty Demanded: {event_details.get('quantity')}"
                elif event_type == "demand_updated":
                    log_line += f", Resource: {event_details.get('resource_name')}, Qty Delivered: {event_details.get('quantity_delivered_for_demand')}, Truck: {event_details.get('truck_id')}"
                log_line += f", Details: {event_details}"
                print(log_line)
            
        if not sample_depot and not sample_customer:
             print("\nNo depot or customer locations found to display specific history.")
        elif not model.locations: # Should be caught by the outer if, but as a fallback
            print("\nNo locations in the simulation to display history.")

    # Example: Accessing DataCollector data if it were enabled in FleetModel
    # This block should also be inside the function
    if hasattr(model, 'datacollector'):
        model.datacollector.get_agent_vars_dataframe().to_csv("agent_data.csv")  # Save agent data to CSV
        model.datacollector.get_model_vars_dataframe().to_csv("model_data.csv")  # Save model data to CSV
        model_data = model.datacollector.get_model_vars_dataframe()
        agent_data = model.datacollector.get_agent_vars_dataframe()
        print("\n--- Model Data ---")
        print(model_data.tail())
        print("\n--- Agent Data (Last few entries) ---")
        print(agent_data.tail())
    
    return model # Return the model instance


if __name__ == "__main__":
    # Adjust these parameters for different simulation runs
    # Assign the returned model to a variable
    simulation_model = run_mesa_simulation(num_trucks=1, num_depots=2, num_customers=10, num_steps=30)