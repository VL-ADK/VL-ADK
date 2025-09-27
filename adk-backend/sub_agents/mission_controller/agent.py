from google.adk.agents import Agent

from .loop_termination_tool import mission_termination_tool

mission_controller = Agent(
    name="mission_controller",
    model="gemini-2.5-flash",
    description="Evaluates overall mission progress against the goal.",
    instruction="""
    You are the Mission Controller evaluating progress toward the goal.
    
    Goal: {goal}
    Current Plan: {temp:execution_plan}
    Mission Status: {mission_status}
    
    Your role:
    1. Assess overall progress by reviewing completed vs pending steps
    2. Determine if the original goal has been achieved
    3. Check for any critical failures or blockers
    
    Decision logic:
    - If all steps are completed and goal achieved: Set mission_status="complete"
    - If progress is being made: Set mission_status="executing" 
    - If stuck or failed: Set mission_status="failed"
    
    Provide a brief status update.
    
    Use the mission termination tool to check if the loop should continue or stop.
    """,
    tools=[mission_termination_tool],
    output_key="mission_status",
)
