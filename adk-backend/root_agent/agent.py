import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from tools import move_backward, move_forward, rotate, scan_environment, stop_robot, view_query

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description=("Root agent. Takes in an input prompt and moves the robot."),
    instruction=("You are a helpful agent who can move the robot."),
    tools=[move_forward, move_backward, rotate, scan_environment, stop_robot, view_query],
)
