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
    for i, (name, loc) in enumerate(model.locations.items()):
        if i < 3: # Print first 3 locations
            print(loc)
            if loc.resources: print(f"  Resources: {loc.resources}")
        elif i >=3:
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
                print(f"Time: {event_time}, Type: {event_type}, Details: {event_details}")
        else:
            print("\nNo Truck agents found to display history.")
    else:
        print("\nNo agents in the simulation to display history.")

    if model.locations:
        sample_loc_name = list(model.locations.keys())[0]
        sample_location = model.locations[sample_loc_name]
        print(f"\n--- Event Log for Location {sample_location.name} ---")
        for event_time, event_type, event_details in sample_location.event_log:
            print(f"Time: {event_time}, Type: {event_type}, Details: {event_details}")
    else:
        print("\nNo locations in the simulation to display history.")

    # Example: Accessing DataCollector data if it were enabled in FleetModel
    if hasattr(model, 'datacollector'):
        model_data = model.datacollector.get_model_vars_dataframe()
        agent_data = model.datacollector.get_agent_vars_dataframe()
        print("\n--- Model Data ---")
        print(model_data.tail())
        print("\n--- Agent Data (Last few entries) ---")
        print(agent_data.tail())


if __name__ == "__main__":
    # You can adjust these parameters for different simulation runs
    run_mesa_simulation(num_trucks=15, num_depots=2, num_customers=10, num_steps=30)