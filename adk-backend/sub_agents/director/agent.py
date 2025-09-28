import datetime

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext

from sub_agents.shared_tools import mission_complete, move_backward, move_forward, rotate, scan_environment, stop_robot, view_query


def initialize_mission_tool(goal: str, tool_context: ToolContext) -> dict:
    """Initialize mission state with goal, status, and create execution plan."""
    tool_context.state["goal"] = goal
    tool_context.state["mission_start_time"] = datetime.datetime.now().isoformat()

    tool_context.state["mission_status"] = "planning"

    return {"status": "Mission initialized", "goal": goal, "mission_status": "planning"}


initialize_mission = FunctionTool(func=initialize_mission_tool)

director = Agent(
    name="director",
    model="gemini-2.5-flash",
    description="Entry point that receives the goal and initializes the mission context.",
    instruction="""
    You are the Director of an autonomous robot mission.
    
    Your role:
    1. Extract the user's goal from their message
    2. Decide if this is a SIMPLE direct command or COMPLEX multi-step goal
    3. For SIMPLE commands: Execute them directly using your tools and call mission_complete
    4. For COMPLEX goals: Use initialize_mission to set up loop-based execution
    
    Decision Logic:
    - SIMPLE commands (e.g., "drive forward 5 feet", "rotate 90 degrees", "scan the room"):
      Execute immediately with your tools, then call mission_complete
    - COMPLEX goals (e.g., "find water bottle and ram it", "explore and find objects"):
      Call initialize_mission to set up Observer+Pilot coordination
    
    Available tools for direct execution:
    - move_forward, move_backward: For movement commands
    - rotate: For turning/rotation commands
    - scan_environment: For scanning/looking commands
    - view_query: For simple object detection
    - stop_robot: For stopping
    - mission_complete: When simple task is done
    """,
    tools=[initialize_mission, move_forward, move_backward, rotate, scan_environment, stop_robot, view_query, mission_complete],
    output_key="mission_initialized",
)
