import datetime
from zoneinfo import ZoneInfo

import requests
from google.adk.agents import Agent


def move_robot(speed: float, duration: float) -> dict:
    """Tool to move the robot at a specified speed for a specified duration (in seconds).

    Args:
        speed (float): The speed to move the robot, in meters per second.
        duration (float): The duration to move the robot, in seconds.

    Returns:
        dict: status and result or error msg.
    """

    print("[ADK-API] Moving robot at speed {speed} for {duration} seconds")
    url = "http://localhost:8889/forward/"
    params = {"speed": speed, "duration": duration}
    response = requests.post(url, params=params)
    return response.json()

def view_query(query: list[str]) -> dict:
    """Tool to view search for a list of objects from the JetBot camera feed.

    Args:
        query (list[str]): A list of objects to search for, each a single word.
        e.g. ["apple", "banana", "orange"]

    Returns:
        dict: status and result or error msg.
    """
    print("[ADK-API] Viewing query: {query}")
    url = "http://localhost:8889/view_query/"
    params = {"query": query}
    response = requests.post(url, params=params)


root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description=("Root agent. Takes in an input prompt and moves the robot."),
    instruction=("You are a helpful agent who can move the robot."),
    tools=[move_robot],
)
