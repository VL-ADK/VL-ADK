import datetime

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext

from sub_agents.shared_tools import mission_complete, move_backward, move_backward_distance, move_forward, move_forward_distance, rotate, scan_environment, stop_robot, view_query


def initialize_mission_tool(goal: str, detailed_plan: str, tool_context: ToolContext) -> dict:
    """Initialize mission state with goal, status, and create execution plan."""
    tool_context.state["goal"] = goal
    tool_context.state["mission_start_time"] = datetime.datetime.now().isoformat()
    tool_context.state["temp:detailed_plan"] = detailed_plan

    tool_context.state["mission_status"] = "planning"

    return {"status": "Mission initialized with plan", "goal": goal, "mission_status": "planning", "detailed_plan": detailed_plan}


initialize_mission = FunctionTool(func=initialize_mission_tool)

director = Agent(
    name="director",
    model="gemini-2.0-flash",
    description="Entry point that receives the goal and initializes the mission context.",
    instruction="""
    You are the Director of an autonomous robot mission.
    
    When sending messages, assume they will be read by the user. Be concise, to the point, and don't include any extra information - particularly about tool calls or the other agents. Act friendly and helpful.
    
    Your role:
    1. Extract the user's goal from their message
    2. Decide if this is a SIMPLE direct command or COMPLEX multi-step goal
    3. For SIMPLE commands: Execute them directly using your tools and call mission_complete
    4. For COMPLEX goals: Use initialize_mission to set up loop-based execution and broadcast your detailed plan to the Observer and Pilot.
    
    Decision Logic:
    - SIMPLE commands are anything done in one tool call (e.g., "drive forward 5 feet", "rotate 90 degrees", "scan the room"):
      Execute immediately with your tools, then call mission_complete
    - COMPLEX goals (e.g., "find water bottle and ram it", "explore and find objects"):
      Call initialize_mission to set up Observer+Pilot coordination
    
    Available tools for direct execution:
    - move_forward, move_backward: For movement commands by time and speed
    - move_forward_distance, move_backward_distance: For movement commands by distance in meters or feet
    - rotate: For turning/rotation commands
    - scan_environment: For scanning/looking commands with optional orientation filtering
    - view_query: For object detection with spatial orientation filtering (horizontal/vertical)
    - stop_robot: For stopping
    - initialize_mission: For complex goals, used to broadcast the users goal and a detailed plan to the Observer and Pilot.
    - mission_complete: When simple task is done
    
    SPATIAL REASONING FOR ORIENTATION FILTERING:
    - view_query and scan_environment now support orientation filtering for precise spatial understanding
    - Use orientation="vertical" for: standing people, upright bottles, doors, tall obstacles
    - Use orientation="horizontal" for: tables, cars, flat surfaces, lying objects
    - This helps distinguish between object states (e.g., upright vs fallen bottle)
    - Include orientation considerations in your detailed plans for complex missions
    """,
    tools=[initialize_mission, move_forward, move_backward, move_forward_distance, move_backward_distance, rotate, scan_environment, stop_robot, view_query, mission_complete],
    output_key="mission_initialized",
)
