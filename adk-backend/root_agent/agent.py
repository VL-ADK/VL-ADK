"""Root agent entry point for the autonomous robot system."""

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from sub_agents import autonomous_robot_system

# Export the composed agent system as root_agent
root_agent = autonomous_robot_system
