from google.adk.tools import FunctionTool, ToolContext


def check_mission_complete_tool(tool_context: ToolContext) -> dict:
    """Checks if mission is complete and escalates to terminate LoopAgent if needed."""

    # Get current mission status and plan
    mission_status = tool_context.state.get("mission_status", "executing")
    execution_plan = tool_context.state.get("temp:execution_plan", [])

    # Count completed vs total steps
    if execution_plan:
        completed_steps = [step for step in execution_plan if step.get("status") == "completed"]
        total_steps = len(execution_plan)
        completion_ratio = len(completed_steps) / total_steps if total_steps > 0 else 0
    else:
        completion_ratio = 0
        total_steps = 0

    # Increment loop count
    loop_count = tool_context.state.get("loop_iteration", 0)
    loop_count += 1
    tool_context.state["loop_iteration"] = loop_count

    response_message = f"Loop iteration {loop_count}: Mission status = {mission_status}, Completion = {completion_ratio:.0%}"

    # Check termination conditions
    if mission_status == "complete":
        print("  Mission complete. Setting escalate=True to stop the LoopAgent.")
        tool_context.actions.escalate = True
        response_message += " Mission complete, stopping loop."
    elif mission_status == "failed":
        print("  Mission failed. Setting escalate=True to stop the LoopAgent.")
        tool_context.actions.escalate = True
        response_message += " Mission failed, stopping loop."
    elif loop_count >= 100:  # Max iterations safety
        print(f"  Max iterations ({loop_count}) reached. Setting escalate=True to stop the LoopAgent.")
        tool_context.actions.escalate = True
        tool_context.state["mission_status"] = "failed"
        response_message += " Max iterations reached, stopping loop."
    else:
        print("  Mission continuing. Loop will continue.")
        response_message += " Loop continues."

    return {"status": "Mission evaluation complete", "message": response_message}


mission_termination_tool = FunctionTool(func=check_mission_complete_tool)
