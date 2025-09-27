"""Root agent entry point for the autonomous robot system."""

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from sub_agents.shared_tools import move_backward, move_forward, rotate, scan_environment, stop_robot, view_query

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description="Root agent for the autonomous robot system.",
    instruction="""
    You are the root agent for the autonomous robot system.
    You are given a goal and you need to achieve it.
    
    You have access to the following tools:
    - move_backward: Move the robot backward
    - move_forward: Move the robot forward
    - rotate: Rotate the robot
    - scan_environment: Scan the environment
    - stop_robot: Stop the robot
    - view_query: View the environment
    
    """,
    tools=[move_backward, move_forward, rotate, scan_environment, stop_robot, view_query],
)
