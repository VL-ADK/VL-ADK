from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from .director.agent import director
from .mission_controller.agent import mission_controller
from .observer.agent import observer
from .operations_manager.agent import operations_manager
from .pilot.agent import pilot
from .strategist.agent import strategist

# Simple execution loop: Mission Controller checks completion and escalates when done
execution_loop = LoopAgent(
    name="execution_loop",
    sub_agents=[
        mission_controller,  # Checks if mission is complete, escalates if done
        operations_manager,  # Coordinates next step
        pilot,  # Executes movement (will add ParallelAgent later)
        observer,  # Processes vision (will add ParallelAgent later)
    ],
    max_iterations=50,
)


# Complete system: Planning phase → Execution loop
autonomous_robot_system = SequentialAgent(
    name="autonomous_robot_system",
    sub_agents=[
        director,  # Initialize mission
        strategist,  # Create execution plan
        execution_loop,  # Execute until complete
    ],
)


__all__ = [
    "director",
    "strategist",
    "mission_controller",
    "operations_manager",
    "pilot",
    "observer",
    "execution_loop",
    "autonomous_robot_system",
]
