"""Tools for robot control and vision processing."""

import base64
import os

import requests
from google.adk.tools import FunctionTool, ToolContext

# Optional: prefer google-genai, fall back to google-generativeai for environments that don't have the new SDK yet.
_GENAI_MODE = None  # "google-genai" | "google-generativeai" | None

try:
    # Newer SDK (google-genai)
    from google import genai as _genai_new  # type: ignore
    from google.genai import types as _genai_types  # type: ignore

    _GENAI_MODE = "google-genai"
except Exception:
    try:
        # Legacy SDK (google-generativeai)
        import google.generativeai as _genai_old  # type: ignore

        _GENAI_MODE = "google-generativeai"
    except Exception:
        _GENAI_MODE = None


# ----------------------------
# Mission control helpers
# ----------------------------
def mission_complete_tool(reason: str, tool_context: ToolContext) -> dict:
    """Terminate the execution loop when the mission is complete.

    Args:
        reason (str): Why the mission is complete (e.g., "Apple found and reached")

    Returns:
        dict: Status of mission completion
    """
    # Update mission status
    tool_context.state["mission_status"] = "complete"

    # Escalate to terminate the LoopAgent
    tool_context.actions.escalate = True

    return {"status": "Mission complete", "reason": reason, "mission_status": "complete", "loop_terminated": True}


mission_complete = FunctionTool(func=mission_complete_tool)


# ----------------------------
# Vision: Primary tool (YOLO-E)
# ----------------------------
def view_query_tool(query: list[str]) -> dict:
    """Tool to view/search for a list of objects from the JetBot camera feed.

    Args:
        query (list[str]): A list of objects to search for. Each query can be 1-3 words, and you can optionally add color queries.
        e.g. ["apple", "banana", "orange"]
        e.g. ["red apple", "green apple", "yellow apple"]

    Note:
        - The "rotation_degree" field is the degree of rotation from the center of the image. Using it may be useful to turn head on towards the object.
        - The bbox and area values are useful for determining distance. A larger bbox and area means the object is likely closer to the view, depending on the object.

    Returns:
        dict: The response from the view_query API with the following fields:
        {
            "annotations": [
                {
                    "class": "query",
                    "confidence": float,
                    "bbox": [x, y, w, h],
                    "center": [x, y],
                    "area": float,
                    "prompt_index": int,
                    "rotation_degree": float
                }
            ],
            "count": 1,
            "timestamp": float,
            "image_shape": [w, h, 3],
            "current_prompts": list[str],
            "model_type": "YOLO-E",
            "motor_data": {
                "left_motor": float,
                "right_motor": float
            },
            "frame_timestamp": float,
            "detection_timestamp": float
        }

    """

    print(f"[ADK-API] Viewing query: {query}")
    url = "http://localhost:8001/yolo/"
    # The YOLO-E API expects a GET request with repeated 'words' query params.
    params = [("words", word) for word in query]
    response = requests.get(url, params=params)
    resp_json = response.json()

    if "annotations" not in resp_json:
        # Defensive: bubble up backend error for agent logic
        err = resp_json.get("error", "Unknown error")
        print(f"[ADK-API] Error from YOLO-E API: {err}")
        return resp_json

    print("[ADK-API] Found the following objects:")
    for annotation in resp_json["annotations"]:
        print(f"  - {annotation['class']} (confidence: {annotation['confidence']})")

    return resp_json


view_query = FunctionTool(func=view_query_tool)


# ------------------------------------------
# Vision: Secondary clarifier (Gemini + b64)
# ------------------------------------------
# def clarify_view_with_gemini_tool(question: str) -> dict:
#     """(Secondary) Ask Gemini for higher-level clarification about the **current annotated** camera image.

#     IMPORTANT:
#       - Use this ONLY for **further clarification** or scene-level reasoning.
#       - The **primary** detection tool is `view_query([...])`.
#       - Phrases like “look closer / further” may trigger this tool.
#       - This calls `/retrieve-annotated-image` (boxes/segments only, no FPS/prompt text).
#         If you want to target specific classes, call `view_query([...])` first to set/promote prompts.

#     Args:
#         question (str): Natural-language question for Gemini about the current annotated image.
#                         (e.g., "Is the bottle to the left of the person?")

#     Returns:
#         dict: {
#             "question": str,
#             "answer": str,
#             "model": "gemini-2.5-flash" | ...,
#             "yolo_count": int,
#             "yolo_prompts": list[str],
#             "timestamp": float,
#             "used_sdk": "google-genai" | "google-generativeai",
#             "error": str (optional)
#         }
#     """
#     print(f"[ADK-API] Clarifying view with Gemini: {question}")

#     # 1) Pull the minimally annotated JPEG (boxes/segments only) as b64
#     try:
#         yolo_url = "http://localhost:8001/retrieve-annotated-image"
#         yolo_resp = requests.get(yolo_url, timeout=10)
#         yolo_json = yolo_resp.json()
#     except Exception as e:
#         return {"question": question, "error": f"Failed to call YOLO route: {e}"}

#     if "error" in yolo_json:
#         return {"question": question, "error": f"YOLO error: {yolo_json.get('error')}"}

#     img_b64 = yolo_json.get("image")
#     if not img_b64:
#         return {"question": question, "error": "YOLO response missing 'image' b64"}

#     try:
#         img_bytes = base64.b64decode(img_b64)
#     except Exception as e:
#         return {"question": question, "error": f"Invalid base64 image from YOLO: {e}"}

#     # 2) Ask Gemini about the image
#     api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
#     if not api_key:
#         return {"question": question, "error": "Missing GOOGLE_API_KEY environment variable"}

#     # Default fast model; you can override with: export GEMINI_MODEL="gemini-1.5-pro"
#     model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

#     try:
#         if _GENAI_MODE == "google-genai":
#             # New SDK
#             client = _genai_new.Client(api_key=api_key)
#             img_part = _genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
#             text_part = _genai_types.Part.from_text(text=question)
#             response = client.models.generate_content(model=model_name, contents=[text_part, img_part])

#             # Extract answer text
#             answer_text = ""
#             # New SDK often exposes .text; fall back to candidate parts
#             if hasattr(response, "text") and response.text:
#                 answer_text = response.text
#             elif hasattr(response, "candidates") and response.candidates:
#                 candidate = response.candidates[0]
#                 if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
#                     for part in candidate.content.parts:
#                         if getattr(part, "text", None):
#                             answer_text = part.text
#                             break

#             if not answer_text:
#                 return {
#                     "question": question,
#                     "error": "No text content found in Gemini response",
#                     "used_sdk": "google-genai",
#                 }

#             return {
#                 "question": question,
#                 "answer": answer_text,
#                 "model": model_name,
#                 "yolo_count": yolo_json.get("count"),
#                 "yolo_prompts": yolo_json.get("prompts", []),
#                 "timestamp": yolo_json.get("timestamp"),
#                 "used_sdk": "google-genai",
#             }

#         elif _GENAI_MODE == "google-generativeai":
#             # Legacy SDK
#             _genai_old.configure(api_key=api_key)
#             model = _genai_old.GenerativeModel(model_name)
#             content_parts = [{"mime_type": "image/jpeg", "data": img_bytes}, question]
#             result = model.generate_content(content_parts)

#             answer_text = ""
#             if hasattr(result, "text") and result.text:
#                 answer_text = result.text
#             elif hasattr(result, "candidates") and result.candidates:
#                 candidate = result.candidates[0]
#                 if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
#                     for part in candidate.content.parts:
#                         if getattr(part, "text", None):
#                             answer_text = part.text
#                             break

#             return {
#                 "question": question,
#                 "answer": answer_text or "",
#                 "model": model_name,
#                 "yolo_count": yolo_json.get("count"),
#                 "yolo_prompts": yolo_json.get("prompts", []),
#                 "timestamp": yolo_json.get("timestamp"),
#                 "used_sdk": "google-generativeai",
#             }

#         else:
#             return {"question": question, "error": "Neither 'google-genai' nor 'google-generativeai' package is installed."}

#     except Exception as e:
#         return {
#             "question": question,
#             "error": f"Gemini request failed: {type(e).__name__}: {e}",
#             "sdk_mode": _GENAI_MODE,
#             "model": model_name,
#         }


# clarify_view_with_gemini = FunctionTool(func=clarify_view_with_gemini_tool)


# ----------------------------
# Robot control (JetBot @8890)
# ----------------------------
_ROBOT_BASE = "http://localhost:8889"


def move_forward_tool(speed: float, duration: float) -> dict:
    """Move the robot forward at specified speed and duration.

    Args:
        speed (float): Measurement of motor speed, between 0.0 and 1.0. This motor speed is completely arbitrary, and is NOT in meters per second.
        duration (float): Duration in seconds.

    Returns:
        dict: Status response from robot API
    """
    print(f"[ADK-API] Moving forward at speed {speed} for {duration} seconds")
    url = f"{_ROBOT_BASE}/forward/"
    params = {"speed": speed}
    if duration is not None:
        params["duration"] = duration

    response = requests.post(url, params=params)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "moving forward",
            "speed": speed,
            "duration": duration,
            "response_text": response.text,
            "status_code": response.status_code,
        }


move_forward = FunctionTool(func=move_forward_tool)


def move_backward_tool(speed: float, duration: float) -> dict:
    """Move the robot backward at specified speed and duration.

    Args:
        speed (float): Measurement of motor speed, between 0.0 and 1.0. This motor speed is completely arbitrary, and is NOT in meters per second.

    Returns:
        dict: Status response from robot API
    """
    print(f"[ADK-API] Moving backward at speed {speed} for {duration} seconds")
    url = f"{_ROBOT_BASE}/backward/"
    params = {"speed": speed}
    if duration is not None:
        params["duration"] = duration

    response = requests.post(url, params=params)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "moving backward",
            "speed": speed,
            "duration": duration,
            "response_text": response.text,
            "status_code": response.status_code,
        }


move_backward = FunctionTool(func=move_backward_tool)


def rotate_tool(angle_in_degrees: float, speed: float) -> dict:
    """Rotate the robot by specified angle (uses unified /rotate/ endpoint).

    API behavior:
      - New API exposes POST /rotate/ with `angle` only.
      - Speed is controlled internally (RobotActions.rotate uses 0.5).
      - We keep `speed` in the tool signature for compatibility, but the endpoint ignores it.

    Args:
        angle_in_degrees (float): Positive = clockwise, Negative = counter-clockwise.
        speed (float): Kept for client UX; not sent to the API.

    Returns:
        dict: Status response from robot API (echoes direction for convenience).
    """
    # Determine direction for client readability
    direction = "clockwise" if angle_in_degrees > 0 else ("counter-clockwise" if angle_in_degrees < 0 else "none")
    print(f"[ADK-API] Rotating {angle_in_degrees} degrees ({direction}); API ignores speed={speed}")

    url = f"{_ROBOT_BASE}/rotate/"
    params = {"angle": angle_in_degrees}

    response = requests.post(url, params=params)
    try:
        result = response.json()
        result["direction"] = direction
        result["requested_speed"] = speed  # informational only
        return result
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "rotating",
            "angle_in_degrees": angle_in_degrees,
            "direction": direction,
            "requested_speed": speed,
            "response_text": response.text,
            "status_code": response.status_code,
        }


rotate = FunctionTool(func=rotate_tool)


def stop_robot_tool() -> dict:
    """Stop the robot immediately."""
    print("[ADK-API] Stopping robot")
    url = f"{_ROBOT_BASE}/stop/"
    response = requests.post(url)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "stopped",
            "message": "Robot stopped",
            "response_text": response.text,
            "status_code": response.status_code,
        }


stop_robot = FunctionTool(func=stop_robot_tool)


def scan_environment_tool(query: list[str]) -> dict:
    """Tool to view/search for a list of objects from the JetBot camera feed.

    Args:
        query (list[str]): A list of objects to search for. Each query can be 1-3 words, and you can optionally add color queries.
        e.g. ["apple", "banana", "orange"]
        e.g. ["red apple", "green apple", "yellow apple"]

    Returns:
        data from the scan_environment API, detailing what items were found in which quadrant.

    """

    print(f"[ADK-API] Scanning environment for: {query}")
    url = f"{_ROBOT_BASE}/scan/"
    # Use query params like view_query does
    params = [("words", word) for word in query]
    response = requests.post(url, params=params)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "scanning",
            "message": "Scan completed",
            "response_text": response.text,
            "status_code": response.status_code,
        }


scan_environment = FunctionTool(func=scan_environment_tool)
