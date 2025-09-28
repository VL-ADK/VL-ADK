"""Tools for robot control and vision processing."""

import base64
import os
from typing import Optional

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
def view_query_tool(query: list[str], orientation: Optional[str]) -> dict:
    """Tool to view/search for a list of objects from the JetBot camera feed with optional orientation filtering.

    Args:
        query (list[str]): A list of objects to search for. Each query can be 1-3 words, and you can optionally add color queries.
        e.g. ["apple", "banana", "orange"]
        e.g. ["red apple", "green apple", "yellow apple"]
        
        orientation (Optional[str]): Filter by object orientation for spatial reasoning:
        - "horizontal": Objects wider than tall (aspect_ratio > 1.0) - tables, cars, laptops, lying objects
        - "vertical": Objects taller than wide (aspect_ratio < 1.0) - people, bottles, doors, standing objects
        - None: No orientation filtering, returns all detected objects

    Spatial Reasoning Notes:
        - Use "horizontal" to find: tables, cars, laptops, books lying flat, horizontal surfaces
        - Use "vertical" to find: people standing, bottles upright, doors, trees, vertical objects
        - The "rotation_degree" field is the degree of rotation from the center of the image for navigation
        - The bbox and area values determine distance - larger bbox/area means closer to camera
        - The "object_orientation" field shows calculated orientation: "horizontal" or "vertical"
        - The "aspect_ratio" field shows width/height ratio for precise spatial understanding

    Returns:
        dict: The response from the view_query API with the following fields:
        {
            "annotations": [
                {
                    "class": "query",
                    "confidence": float,
                    "bbox": [x1, y1, x2, y2],
                    "center": [x, y],
                    "area": float,
                    "prompt_index": int,
                    "rotation_degree": float,
                    "object_orientation": "horizontal" | "vertical",
                    "aspect_ratio": float
                }
            ],
            "count": 1,
            "total_detected": int,
            "orientation_filter": str | None,
            "timestamp": float,
            "image_shape": [h, w, 3],
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

    print(f"[ADK-API] Viewing query: {query}" + (f" with orientation: {orientation}" if orientation else ""))
    url = "http://localhost:8001/yolo/"
    # The YOLO-E API expects a GET request with repeated 'words' query params.
    params = [("words", word) for word in query]
    if orientation:
        params.append(("orientation", orientation))
    
    response = requests.get(url, params=params)
    resp_json = response.json()

    if "annotations" not in resp_json:
        # Defensive: bubble up backend error for agent logic
        err = resp_json.get("error", "Unknown error")
        print(f"[ADK-API] Error from YOLO-E API: {err}")
        return resp_json

    print("[ADK-API] Found the following objects:")
    for annotation in resp_json["annotations"]:
        orientation_info = f" ({annotation.get('object_orientation', 'unknown')} - {annotation.get('aspect_ratio', 0):.2f})" if annotation.get('object_orientation') else ""
        print(f"  - {annotation['class']} (confidence: {annotation['confidence']:.2f}){orientation_info}")

    if orientation:
        total = resp_json.get('total_detected', len(resp_json['annotations']))
        filtered = len(resp_json['annotations'])
        print(f"[ADK-API] Orientation filter '{orientation}': {filtered}/{total} objects match")

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


def move_backward_distance_tool(distance_in_meters: Optional[float], distance_in_feet: Optional[float]) -> dict:
    """Move the robot backward a given amount of meters.

    Args:
        distance_in_meters (float): The amount of meters to move backward. Optional, but if provided, distance_in_feet will be ignored.
        distance_in_feet (float): The amount of feet to move backward. Optional, but if provided, distance_in_meters will be ignored.

    SPATIAL REASONING FOR MOVING (FORWARD/BACKWARD):
    - The diameter of the robot's wheels are 0.065 meters. (65 millimeters)
    - The circumference of the robot's wheels are 0.204 meters. (204 millimeters)
    - The radius of the robot's wheels are 0.0325 meters. (32.5 millimeters)

    Returns:
        dict: Status response from robot API
    """
    if distance_in_meters is not None:
        distance = distance_in_meters
    elif distance_in_feet is not None:
        distance = distance_in_feet * 0.3048
    else:
        return {"error": "No distance provided"}

    # Calculate duration in seconds
    duration = distance / 0.572  # 0.572 m/s is the default speed

    return move_backward_tool(speed=0.5, duration=duration)


move_backward_distance = FunctionTool(func=move_backward_distance_tool)


def move_forward_distance_tool(distance_in_meters: Optional[float], distance_in_feet: Optional[float]) -> dict:
    """Move the robot forward a given amount of meters.

    Args:
        distance_in_meters (float): The amount of meters to move forward. Optional, but if provided, distance_in_feet will be ignored.
        distance_in_feet (float): The amount of feet to move forward. Optional, but if provided, distance_in_meters will be ignored.

    SPATIAL REASONING FOR MOVING (FORWARD/BACKWARD):
    - The diameter of the robot's wheels are 0.065 meters. (65 millimeters)
    - The circumference of the robot's wheels are 0.204 meters. (204 millimeters)
    - The radius of the robot's wheels are 0.0325 meters. (32.5 millimeters)

    Returns:
        dict: Status response from robot API
    """
    if distance_in_meters is not None:
        distance = distance_in_meters
    elif distance_in_feet is not None:
        distance = distance_in_feet * 0.3048
    else:
        return {"error": "No distance provided"}

    # Calculate duration in seconds
    duration = distance / 0.572  # 0.572 m/s is the default speed

    return move_forward_tool(speed=0.5, duration=duration)


move_forward_distance = FunctionTool(func=move_forward_distance_tool)


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


def scan_environment_tool(query: list[str], orientation: Optional[str]) -> dict:
    """Tool to scan environment for objects with optional orientation filtering for spatial reasoning.

    Args:
        query (list[str]): A list of objects to search for. Each query can be 1-3 words, and you can optionally add color queries.
        e.g. ["apple", "banana", "orange"]
        e.g. ["red apple", "green apple", "yellow apple"]
        
        orientation (Optional[str]): Filter by object orientation for spatial reasoning:
        - "horizontal": Find objects wider than tall (tables, cars, laptops, lying objects)
        - "vertical": Find objects taller than wide (people, bottles, doors, standing objects)
        - None: No orientation filtering, returns all detected objects

    Spatial Reasoning:
        - Horizontal objects often represent: surfaces (tables), vehicles (cars), devices (laptops)
        - Vertical objects often represent: obstacles (people), containers (bottles), passages (doors)
        - Use orientation filtering to distinguish between similar objects in different positions
        - Example: "bottle" with "vertical" = upright bottle, "horizontal" = fallen/lying bottle

    Returns:
        dict: The response from the scan_environment API with spatial orientation data:
        - Each annotation includes "object_orientation" and "aspect_ratio" fields
        - "total_detected" shows objects found before orientation filtering
        - "count" shows objects remaining after orientation filtering

    """

    print(f"[ADK-API] Scanning environment for: {query}" + (f" with orientation: {orientation}" if orientation else ""))

    # First, set the prompts in the YOLO model so it can detect these objects
    print(f"[ADK-API] Setting YOLO prompts to: {query}")
    yolo_prompts_url = "http://localhost:8001/prompts/"
    try:
        prompts_response = requests.post(yolo_prompts_url, json=query)
        if prompts_response.status_code != 200:
            print(f"[ADK-API] Warning: Failed to set YOLO prompts: {prompts_response.text}")
    except Exception as e:
        print(f"[ADK-API] Warning: Failed to set YOLO prompts: {e}")

    # Now call the JetBot scan endpoint with orientation filtering
    url = f"{_ROBOT_BASE}/scan/"
    # Use query params like view_query does
    params = [("words", word) for word in query]
    if orientation:
        params.append(("orientation", orientation))
        
    response = requests.post(url, params=params)
    print(f"[ADK-API] Scan response: {response.json()}")
    try:
        result = response.json()
        
        # Add spatial reasoning info to the response
        if orientation and "annotations" in result:
            print(f"[ADK-API] Spatial filter '{orientation}': Found {len(result.get('annotations', []))} {orientation} objects")
            
        return result
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "scanning",
            "message": "Scan completed",
            "response_text": response.text,
            "status_code": response.status_code,
        }


scan_environment = FunctionTool(func=scan_environment_tool)


def get_bounding_box_percentage_tool(bbox: list[int]) -> dict:
    """Get the percentage of the camera view that is covered by the bounding box.

    Args:
        bbox (list[int]): The bounding box of the object.

    Returns:
        float: The percentage of the camera view that is covered by the bounding box.
    """
    # Camera aspect is 1640x1232
    camera_area = 1640 * 1232
    # Bounding box is in the format [top_left, bottom_left, top_right, bottom_right]
    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    print(f"[ADK-API] Bounding box: {bbox}")
    print(f"[ADK-API] Bounding box area: {bbox_area}, Camera area: {camera_area}")
    return (bbox_area / camera_area) * 100


get_bounding_box_percentage = FunctionTool(func=get_bounding_box_percentage_tool)
