import datetime

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext


def initialize_mission_tool(goal: str, tool_context: ToolContext) -> dict:
    """Initialize mission state with goal and status."""
    tool_context.state["goal"] = goal
    tool_context.state["mission_status"] = "planning"
    tool_context.state["mission_start_time"] = datetime.datetime.now().isoformat()

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
    2. Use the initialize_mission tool to set up shared memory
    3. Acknowledge the mission has been initialized
    
    Call initialize_mission with the user's goal to set up the shared state.
    Keep your response brief and professional.
    """,
    tools=[initialize_mission],
    output_key="mission_initialized",
)
