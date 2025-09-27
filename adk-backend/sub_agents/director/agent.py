import datetime

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext


def initialize_mission_tool(goal: str, tool_context: ToolContext) -> dict:
    """Initialize mission state with goal, status, and create execution plan."""
    tool_context.state["goal"] = goal
    tool_context.state["mission_status"] = "executing"
    tool_context.state["mission_start_time"] = datetime.datetime.now().isoformat()

    # Create a simple execution plan based on the goal
    if "find" in goal.lower() and "apple" in goal.lower():
        plan = """1. Scan environment for initial overview
2. Search for 'apple' using vision
3. If apple found, move towards it
4. If no apple found, rotate and search again
5. Confirm apple identification using Gemini
6. Navigate to apple location
7. Stop when apple is reached"""
    else:
        plan = f"""1. Scan environment to understand surroundings
2. Search for objects related to: {goal}
3. Move towards target when identified
4. Confirm target and complete mission"""

    tool_context.state["temp:execution_plan"] = plan

    return {"status": "Mission initialized with plan", "goal": goal, "mission_status": "executing"}


initialize_mission = FunctionTool(func=initialize_mission_tool)

director = Agent(
    name="director",
    model="gemini-2.5-flash",
    description="Entry point that receives the goal and initializes the mission context.",
    instruction="""
    You are the Director of an autonomous robot mission.
    
    Your role:
    1. Extract the user's goal from their message
    2. Use the initialize_mission tool to set up shared memory
    3. Acknowledge the mission has been initialized
    
    Call initialize_mission with the user's goal to set up the shared state.
    Keep your response brief and professional.
    """,
    tools=[initialize_mission],
    output_key="mission_initialized",
)
