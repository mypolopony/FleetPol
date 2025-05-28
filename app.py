import solara_patch  # must be imported before solara runs
import solara
from mesa.visualization.solara_viz import SolaraViz
from model import FleetModel

# Define initial model parameters
model_params = {
    "num_trucks": 5,
    "num_depots": 1,
    "num_customers": 10,
    "map_width": 50,
    "map_height": 50,
}

def agent_portrayal(agent):
    if hasattr(agent, "pos"):
        print(f"Portraying agent: {agent.name} at {agent.pos}")
        return {
            "shape": "circle",
            "color": "blue",
            "size": 5,
            "x": agent.pos[0],
            "y": agent.pos[1],
        }
    else:
        print(f"Agent {agent.name} has no position!")
        return None

@solara.component
def Page():
    return SolaraViz(
        model=FleetModel,
        model_params=model_params,
        agent_portrayal=agent_portrayal,
        measures=["Step count"],
        name="Fleet Simulation",
    )