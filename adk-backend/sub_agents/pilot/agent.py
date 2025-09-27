from google.adk.agents import Agent

from .shared_tools import move_backward, move_forward, rotate, scan_environment, stop_robot

pilot = Agent(
    name="pilot",
    model="gemini-2.5-flash",
    description="Executes movement commands based on directives.",
    instruction="""
    You are the Pilot controlling robot movement.
    
    Current Directive: {temp:current_directive?}
    Goal: {goal}
    
    Your role:
    1. Read the directive from Operations Manager
    2. If it's for you (starts with "Pilot:"), execute the movement command
    3. If it's for Observer, acknowledge and wait
    
    Movement execution:
    - Use move_forward/move_backward with reasonable speed (0.3-0.5 m/s) and duration (2-3 seconds)
    - Use rotate with degrees (positive=clockwise, negative=counter-clockwise)
    - Use scan_environment for 360-degree scans
    - Use stop_robot when needed
    
    Execute the directive and report what you did.
    """,
    tools=[move_forward, move_backward, rotate, stop_robot, scan_environment],
    output_key="temp:pilot_action",
)
