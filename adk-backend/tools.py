"""Tools for robot control and vision processing."""

import base64
import os

import requests

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


def view_query(query: list[str]) -> dict:
    """Tool to view/search for a list of objects from the JetBot camera feed.

    Args:
        query (list[str]): A list of objects to search for. Each query can be 1-3 words, and you can optionally add color queries.
        e.g. ["apple", "banana", "orange"]
        e.g. ["red apple", "green apple", "yellow apple"]

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
                    "prompt_index": int
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

    # Defensive: handle error response (no 'annotations' key)
    if "annotations" not in resp_json:
        print(f"[ADK-API] Error from YOLO-E API: {resp_json.get('error', 'Unknown error')}")
        return resp_json

    print("[ADK-API] Found the following objects:")
    for annotation in resp_json["annotations"]:
        print(f"  - {annotation['class']} (confidence: {annotation['confidence']})")

    return resp_json


def clarify_view_with_gemini(question: str) -> dict:
    """(Secondary) Ask Gemini for clarification about the current annotated camera image.

    IMPORTANT:
      - Use this ONLY for **further clarification** or higher-level reasoning about the scene.
      - Your **primary** tool for detections is `view_query([...])`.
      - This helper uses `/retrieve-annotated-image` from the YOLO backend and the **current prompts**.
        If you want to target specific classes, call `view_query([...])` first to set/promote those prompts.

    Args:
        question (str): Natural-language question for Gemini about the *current* annotated image
                        (e.g., "Is the bottle to the left of the person?").

    Returns:
        dict: {
            "question": str,
            "answer": str,
            "model": "gemini-1.5-flash" | "gemini-1.5-pro" | ...,
            "yolo_count": int,
            "yolo_prompts": list[str],
            "timestamp": float,
            "used_sdk": "google-genai" | "google-generativeai",
            "error": str (optional)
        }
    """
    # 1) Pull the minimally annotated JPEG (boxes/segments only) as b64
    try:
        yolo_url = "http://localhost:8001/retrieve-annotated-image"
        yolo_resp = requests.get(yolo_url, timeout=10)
        yolo_json = yolo_resp.json()
    except Exception as e:
        return {"question": question, "error": f"Failed to call YOLO route: {e}"}

    if "error" in yolo_json:
        return {"question": question, "error": f"YOLO error: {yolo_json.get('error')}"}

    img_b64 = yolo_json.get("image")
    if not img_b64:
        return {"question": question, "error": "YOLO response missing 'image' b64"}

    try:
        img_bytes = base64.b64decode(img_b64)
    except Exception as e:
        return {"question": question, "error": f"Invalid base64 image from YOLO: {e}"}

    # 2) Ask Gemini about the image
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        return {"question": question, "error": "Missing GOOGLE_API_KEY environment variable"}

    # Default fast model; tweak if you prefer 'gemini-1.5-pro'
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    try:
        if _GENAI_MODE == "google-genai":
            # New SDK
            client = _genai_new.Client(api_key=api_key)
            img_part = _genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            result = client.responses.generate(
                model=model_name,
                input=[img_part, _genai_types.Part.from_text(question)],
            )
            # The new SDK returns a slightly different shape
            answer_text = ""
            if hasattr(result, "output_text"):
                answer_text = result.output_text
            elif hasattr(result, "candidates") and result.candidates:
                # Best-effort extraction
                answer_text = getattr(result.candidates[0], "content", {}).get("parts", [{}])[0].get("text", "")
            return {
                "question": question,
                "answer": answer_text,
                "model": model_name,
                "yolo_count": yolo_json.get("count"),
                "yolo_prompts": yolo_json.get("prompts", []),
                "timestamp": yolo_json.get("timestamp"),
                "used_sdk": "google-genai",
            }

        elif _GENAI_MODE == "google-generativeai":
            # Legacy SDK
            _genai_old.configure(api_key=api_key)
            model = _genai_old.GenerativeModel(model_name)
            # Send as image bytes + question
            # SDK accepts dict with mime_type/data or just bytes in some versions
            result = model.generate_content([{"mime_type": "image/jpeg", "data": img_bytes}, question])
            # Extract text
            answer_text = getattr(result, "text", None)
            if not answer_text and getattr(result, "candidates", None):
                # Best-effort extraction
                parts = result.candidates[0].content.parts
                if parts:
                    answer_text = getattr(parts[0], "text", None) or str(parts[0])
            return {
                "question": question,
                "answer": answer_text or "",
                "model": model_name,
                "yolo_count": yolo_json.get("count"),
                "yolo_prompts": yolo_json.get("prompts", []),
                "timestamp": yolo_json.get("timestamp"),
                "used_sdk": "google-generativeai",
            }

        else:
            return {"question": question, "error": "Neither 'google-genai' nor 'google-generativeai' package is installed."}

    except Exception as e:
        return {"question": question, "error": f"Gemini request failed: {e}"}


def move_forward(speed: float, duration: float) -> dict:
    """Move the robot forward at specified speed and duration.

    Args:
        speed (float): Speed to move forward in meters per second. Max speed is 3 m/s.
        duration (float): Duration in seconds.

    Returns:
        dict: Status response from robot API
    """
    print(f"[ADK-API] Moving forward at speed {speed} for {duration} seconds")
    url = "http://localhost:8889/forward/"
    params = {"speed": speed}
    if duration is not None:
        params["duration"] = duration

    response = requests.post(url, params=params)

    # Handle potential JSON decode errors
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


def move_backward(speed: float, duration: float) -> dict:
    """Move the robot backward at specified speed and duration.

    Args:
        speed (float): Speed to move backward in meters per second. Max speed is 3 m/s.
        duration (float): Duration in seconds.

    Returns:
        dict: Status response from robot API
    """
    print(f"[ADK-API] Moving backward at speed {speed} for {duration} seconds")
    url = "http://localhost:8889/backward/"
    params = {"speed": speed}
    if duration is not None:
        params["duration"] = duration

    response = requests.post(url, params=params)

    # Handle potential JSON decode errors
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


def rotate(angle_in_degrees: float, speed: float = 0.5) -> dict:
    """Rotate the robot by specified angle with unified direction handling.

    This function replaces the deprecated turn_left and turn_right functions.
    It provides a unified interface for robot rotation with intuitive direction handling.

    Args:
        angle_in_degrees (float): Rotation angle in degrees.
            - Positive values: Rotate clockwise (right) - e.g., 90, 180, 360
            - Negative values: Rotate counter-clockwise (left) - e.g., -90, -180, -360
            - Zero: No rotation (returns success immediately)
        speed (float): Rotation speed in meters per second.
            - Range: 0.1 to 3.0 m/s
            - Default: 0.5 m/s
            - Higher speeds = faster rotation
            - Lower speeds = more precise rotation

    Returns:
        dict: Status response from robot API containing:
            - status: "rotating" or error status
            - angle_in_degrees: The requested rotation angle
            - speed: The rotation speed used
            - direction: "clockwise" or "counter-clockwise"
            - response_text: Raw API response (if JSON decode fails)
            - status_code: HTTP status code
    """
    # Handle zero rotation
    if angle_in_degrees == 0:
        return {
            "status": "no_rotation",
            "angle_in_degrees": 0,
            "speed": speed,
            "direction": "none",
            "message": "No rotation requested",
        }

    # Determine direction and endpoint
    if angle_in_degrees > 0:
        direction = "clockwise"
        endpoint = "right"
        print(f"[ADK-API] Rotating {angle_in_degrees} degrees {direction} at speed {speed}")
    else:
        direction = "counter-clockwise"
        endpoint = "left"
        # Convert negative angle to positive for API call
        angle_in_degrees = abs(angle_in_degrees)
        print(f"[ADK-API] Rotating {angle_in_degrees} degrees {direction} at speed {speed}")

    # Make API call
    url = f"http://localhost:8889/{endpoint}/"
    params = {"speed": speed, "angle": angle_in_degrees}

    response = requests.post(url, params=params)

    # Handle potential JSON decode errors
    try:
        result = response.json()
        # Add direction information to the response
        result["direction"] = direction
        return result
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "rotating",
            "angle_in_degrees": angle_in_degrees,
            "speed": speed,
            "direction": direction,
            "response_text": response.text,
            "status_code": response.status_code,
        }


def stop_robot() -> dict:
    """Stop the robot immediately.

    Returns:
        dict: Status response from robot API
    """
    print("[ADK-API] Stopping robot")
    url = "http://localhost:8889/stop/"
    response = requests.post(url)

    # Handle potential JSON decode errors
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        # If the response is not JSON, return a status dict
        return {
            "status": "stopped",
            "message": "Robot stopped",
            "response_text": response.text,
            "status_code": response.status_code,
        }


def scan_environment() -> dict:
    """Perform a 360-degree scan of the environment.

    Returns:
        dict: Status response from robot API
    """
    print("[ADK-API] Scanning environment")
    url = "http://localhost:8889/scan/"
    response = requests.post(url)

    # Handle potential JSON decode errors
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        # If the response is not JSON, return a status dict
        return {
            "status": "scanning",
            "message": "Scan completed",
            "response_text": response.text,
            "status_code": response.status_code,
        }
