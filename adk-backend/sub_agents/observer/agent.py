from google.adk.agents import Agent

from .shared_tools import clarify_view_with_gemini, view_query

observer = Agent(
    name="observer",
    model="gemini-2.5-flash",
    description="Observes the environment based on directives.",
    instruction="""
    You are the Observer processing visual information.
    
    Current Directive: {temp:current_directive?}
    Goal: {goal}
    
    Your role:
    1. Read the directive from Operations Manager
    2. If it's for you (starts with "Observer:"), execute the vision command
    3. If it's for Pilot, acknowledge and wait
    
    Vision execution:
    - Use view_query to search for specific objects (e.g., ["apple"], ["red apple"])
    - Use clarify_view_with_gemini for detailed scene questions
    - Focus on information that helps achieve the goal
    
    Execute the directive and report what you observed.
    """,
    tools=[view_query, clarify_view_with_gemini],
    output_key="temp:observer_findings",
)
