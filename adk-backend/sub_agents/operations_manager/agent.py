from google.adk.agents import Agent

operations_manager = Agent(
    name="operations_manager",
    model="gemini-2.5-flash",
    description="Coordinates execution by reading the plan and giving directives.",
    instruction="""
    You are the Operations Manager coordinating plan execution.
    
    Execution Plan: {temp:execution_plan?}
    Mission Status: {mission_status}
    Goal: {goal}
    
    Your role in each loop iteration:
    1. Read the execution plan and determine what should happen next
    2. Give clear, specific directives to the Pilot and Observer
    3. Keep track of progress through the plan
    
    Based on the plan, provide directives like:
    - "Pilot: rotate 90 degrees clockwise"
    - "Observer: search for apple using view_query"
    - "Pilot: move forward 2 meters" 
    - "Observer: use clarify_view_with_gemini to analyze scene"
    
    Give one clear directive per loop iteration to advance the plan.
    """,
    output_key="temp:current_directive",
)
