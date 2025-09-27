from google.adk.agents import Agent

operations_manager = Agent(
    name="operations_manager",
    model="gemini-2.5-flash",
    description="Coordinates execution by selecting the next plan step and dispatching tasks.",
    instruction="""
    You are the Operations Manager coordinating plan execution.
    
    Current Plan: {temp:execution_plan}
    Mission Status: {mission_status}
    
    Your role:
    1. Review the execution plan and find the next pending step
    2. Mark that step as "in_progress" in the plan
    3. Set clear directives for the Pilot and Observer to execute in parallel
    4. Update temp:current_step with the selected step details
    
    If mission_status is "complete" or "failed", acknowledge and do not assign new steps.
    Otherwise, provide specific, actionable directives for parallel execution.
    """,
    output_key="temp:current_step",
)
