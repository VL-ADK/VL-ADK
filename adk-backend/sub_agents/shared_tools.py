"""Shared tools for step completion tracking in the loop execution system."""

from google.adk.tools import FunctionTool, ToolContext


def complete_step_tool(step_id: int, result: str, tool_context: ToolContext) -> dict:
    """Mark a step as completed and record the result."""
    execution_plan = tool_context.state.get("temp:execution_plan", [])

    # Find and update the step
    step_updated = False
    for step in execution_plan:
        if step.get("id") == step_id:
            step["status"] = "completed"
            step["result"] = result
            step_updated = True
            break

    if step_updated:
        tool_context.state["temp:execution_plan"] = execution_plan
        return {"status": "Step completed", "step_id": step_id, "result": result}
    else:
        return {"status": "Step not found", "step_id": step_id}


complete_step = FunctionTool(func=complete_step_tool)
