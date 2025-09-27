import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
import requests

def move_robot(speed: float, duration: float) -> dict:
    """Tool to move the robot at a specified speed for a specified duration (in seconds).

    Args:
        speed (float): The speed to move the robot.
        duration (float): The duration to move the robot.

    Returns:
        dict: status and result or error msg.
    """
    
    print("[ADK-API] Moving robot at speed {speed} for {duration} seconds")
    url = "http://localhost:8889/forward/"
    params = {
        "speed": speed,
        "duration": duration
    }
    response = requests.post(url, params=params)
    return response.json()

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description=(
        "Root agent. Takes in an input prompt and moves the robot."
    ),
    instruction=(
        "You are a helpful agent who can move the robot."
    ),
    tools=[move_robot],
)