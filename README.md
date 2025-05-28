# Fleet POL (Patterns of Life) Simulator

This project simulates a fleet of trucks managing resources (like "widgets") between depots and customers. It is built using the Mesa agent-based modeling framework.

## Core Concepts

The simulation revolves around a few key components:

*   **Trucks (`agents.py`):** These are Mesa agents that move between locations, load cargo at depots, and unload cargo at customer sites to fulfill demands. Each truck maintains a history of its actions and a cargo manifest.
*   **Locations (`environment.py`):** These represent physical sites in the simulation.
    *   **Depots:** Locations where resources are produced and stored. Trucks visit depots to load cargo. Depots have production capabilities (e.g., producing "widgets" at a certain rate up to a capacity).
    *   **Customers:** Locations that generate demands for resources. Trucks visit customers to unload cargo and fulfill these demands.
*   **Fleet Model (`model.py`):** This is the main Mesa model that orchestrates the simulation. It initializes trucks and locations, manages the simulation steps, and includes logic for:
    *   Resource production at depots.
    *   Demand generation at customer sites.
    *   Assigning routes to trucks, prioritizing those that can fulfill active demands.
*   **Simulation Runner (`main.py`):** This script initializes and runs the `FleetModel`, printing out initial setup details and event logs for sample agents and locations after the simulation completes.
*   **Web Application (`app.py`, `solara_patch.py`):** (Details to be added - currently these files exist but their integration with the core simulation logic for visualization or interaction is not fully detailed yet. There seem to be problems with `solara` and the most up to date version of Mesa)

## Simulation Flow

1.  **Initialization (`model.py`, `main.py`):**
    *   The `FleetModel` creates a specified number of depots and customer locations.
    *   Depots are initialized with some stock of resources (e.g., "widgets") and production capabilities.
    *   Customers may start with initial demands for resources.
    *   Truck agents are created and placed at starting depots.
2.  **Simulation Step (`model.py` - `FleetModel.step()`):**
    *   **Data Collection:** (If enabled) Mesa's DataCollector records model and agent-level variables.
    *   **Resource Production:** Depots produce resources according to their defined rates and capacities.
    *   **Agent Actions:** Each truck agent performs its `step()` logic:
        *   If en route, it "arrives" at its destination.
        *   If idle at a depot, it may load cargo (e.g., "widgets") if available and if it has capacity. The decision to load might be influenced by planned routes or demands.
        *   If idle at a customer, it may unload cargo to fulfill pending demands at that location.
        *   If it has a route and is ready to move, it departs for the next location.
    *   **Demand Generation:** New demands may be randomly generated at customer locations.
    *   **Route Assignment:** Idle trucks at depots may be assigned new routes, with a preference for routes that service customers with active demands.

## Key Features

*   **Resource Management:** Trucks transport resources from production sites (depots) to consumption sites (customers).
*   **Demand Fulfillment:** The system models customer demands and the trucks' efforts to satisfy them.
*   **Event Logging:** Both trucks and locations maintain detailed event logs, capturing actions like creation, movement, loading/unloading cargo, resource consumption/addition, and demand status changes.
*   **Agent-Based:** Leverages the Mesa framework for managing agent behaviors and interactions.

## How to Run

1.  Ensure you have Python and the Mesa library installed.
    ```bash
    pip install mesa
    ```
2.  Run the main simulation script:
    ```bash
    python main.py
    ```
    This will run a console-based simulation and print logs to the terminal. The parameters for the number of trucks, depots, customers, and simulation steps can be adjusted in the `if __name__ == "__main__":` block of `main.py`.

## Files

*   **`main.py`**: Main script to run the simulation and print outputs.
*   **`model.py`**: Defines the `FleetModel` class, orchestrating the simulation.
*   **`agents.py`**: Defines the `Truck` agent class.
*   **`environment.py`**: Defines the `Location` class (used for Depots and Customers).
*   **`app.py`**: (for a web-based visualization or interface - to be detailed further).
*   **`solara_patch.py`**: (related to the re-routing notebook extensions).
*   **`README.md`**: This file.

## Sample Output

For one truck:

```csv
Step  AgentID  Status                             Location      Cargo  Comment
1     1        idle_at_depot                      Depot-B       0 	  Truck us waiting at the depot	
2     1        idle_at_depot                      Depot-B       0      There's only a 30% it gets a route
3     1        idle_at_depot                      Depot-B       0      Still waiting for that 30%
4     1        idle_at_depot                      Depot-B       0      Still waiting
5     1        pending_load_for_route             Depot-B       0      Receives a route
6     1        loading_at_depot                   Depot-B       968    Loads materials based on customer domands
7     1        pending_departure_to_Customer-008  Depot-B       968	  Waiting to travel to first customer (WHY?)
8     1        en_route                           Customer-008  968    Arrives at first customer 
9     1        idle_at_customer                   Customer-008  968    Waiting tick
10    1        finished_unloading                 Customer-008  902    Finished unloading materials across multiple orders (could probably expand for each order at that customer)
11    1        en_route                           Customer-009  902    Immediately takes off and arrives at the next route (should probably be idle before)
12    1        idle_at_customer                   Customer-009  902    Waiting tick
13    1        finished_unloading                 Customer-009  753    Finished unloading materials
14    1        en_route                           Depot-B       753    Back to the depot
15    1        idle_at_depot                      Depot-B       753    Waiting to refill or new route
```

See more complicated outputs in `output/`