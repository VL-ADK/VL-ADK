from google.adk.agents import Agent

from .loop_termination_tool import mission_termination_tool

mission_controller = Agent(
    name="mission_controller",
    model="gemini-2.5-flash",
    description="Evaluates mission progress and decides when to stop the loop.",
    instruction="""
    You are the Mission Controller evaluating mission progress.
    
    Goal: {goal}
    Execution Plan: {temp:execution_plan?}
    Mission Status: {mission_status}
    Recent Actions: {temp:pilot_action?} | {temp:observer_findings?}
    
    Your role:
    1. Assess if the goal has been achieved based on recent actions and findings
    2. Use the mission termination tool to check completion and stop loop if done
    3. Provide a brief progress update
    
    Check for completion:
    - Has the goal been achieved? (e.g., apple found, location reached)
    - Are we making progress or stuck?
    - Should the loop continue or terminate?
    
    Use mission_termination_tool to evaluate and potentially stop the loop.
    """,
    tools=[mission_termination_tool],
    output_key="mission_status",
)
