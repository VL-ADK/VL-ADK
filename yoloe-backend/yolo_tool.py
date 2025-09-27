"""
YOLO-E Tool for ADK Agents
Provides a simple interface for agents to get object detection results using YOLO-E open-vocabulary capabilities.
"""

import requests
from typing import List, Dict, Optional
import time

YOLO_API_URL = "http://localhost:8001"

def get_yolo_annotations(target_words: Optional[List[str]] = None, timeout: int = 5) -> Dict:
    """
    Get YOLO-E object detection annotations from the current camera stream.
    This will automatically set prompts if target_words is provided.
    
    Args:
        target_words: Optional list of object classes to detect (e.g., ["person", "car", "bottle"])
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with detection results including current_prompts
    """
    try:
        params = {}
        if target_words:
            params["words"] = target_words
            
        response = requests.get(
            f"{YOLO_API_URL}/yolo/", 
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        return {
            "error": "YOLO-E API timeout",
            "annotations": [],
            "count": 0
        }
    except requests.exceptions.ConnectionError:
        return {
            "error": "Cannot connect to YOLO-E API - is it running?",
            "annotations": [],
            "count": 0
        }
    except Exception as e:
        return {
            "error": f"YOLO-E API error: {str(e)}",
            "annotations": [],
            "count": 0
        }

def set_prompts(prompts: List[str], timeout: int = 3) -> Dict:
    """
    Set new open-vocabulary prompts for YOLO-E detection.
    
    Args:
        prompts: List of object classes to detect
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with success status and current prompts
    """
    try:
        response = requests.post(
            f"{YOLO_API_URL}/prompts/",
            json=prompts,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to set prompts: {str(e)}"
        }

def get_current_prompts(timeout: int = 3) -> Dict:
    """Get currently active YOLO-E prompts."""
    try:
        response = requests.get(f"{YOLO_API_URL}/prompts/", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "current_prompts": [],
            "error": f"Failed to get prompts: {str(e)}"
        }

def check_yolo_health() -> Dict:
    """Check if YOLO backend is healthy and connected."""
    try:
        response = requests.get(f"{YOLO_API_URL}/health/", timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def find_objects(target_classes: List[str]) -> Dict:
    """
    Simplified interface to find specific objects.
    
    Args:
        target_classes: List of object classes to look for
        
    Returns:
        Simplified results with just essential information
    """
    results = get_yolo_annotations(target_classes)
    
    if "error" in results:
        return results
    
    # Simplify results for agents
    simplified = {
        "objects_found": results.get("count", 0),
        "target_detected": results.get("count", 0) > 0,
        "objects": []
    }
    
    for annotation in results.get("annotations", []):
        simplified["objects"].append({
            "class": annotation["class"],
            "confidence": annotation["confidence"],
            "center": annotation["center"],
            "size": annotation["area"]
        })
    
    return simplified

# Example usage functions for common robot tasks
def scan_for_person() -> bool:
    """Check if any person is detected."""
    result = find_objects(["person"])
    return result.get("target_detected", False)

def scan_for_obstacles() -> List[str]:
    """Get list of potential obstacles."""
    obstacle_classes = ["person", "car", "bicycle", "motorcycle", "chair", "couch"]
    result = get_yolo_annotations(obstacle_classes)
    
    if "error" in result:
        return []
    
    return [obj["class"] for obj in result.get("annotations", [])]

def find_target_object(target: str) -> Optional[Dict]:
    """Find a specific target object and return its position."""
    result = find_objects([target])
    
    if result.get("objects_found", 0) > 0:
        # Return the object with highest confidence
        objects = result["objects"]
        best_object = max(objects, key=lambda x: x["confidence"])
        return {
            "found": True,
            "class": best_object["class"],
            "confidence": best_object["confidence"],
            "center": best_object["center"],
            "direction": "center"  # Could be enhanced with relative positioning
        }
    
    return {"found": False}

def save_debug_image(target_words: Optional[List[str]] = None, timeout: int = 10) -> Dict:
    """
    Save current frame with YOLO annotations to debug directory.
    
    Args:
        target_words: Optional list of object classes to detect and annotate
        timeout: Request timeout in seconds (longer for image processing)
        
    Returns:
        Dictionary with save status and file paths
    """
    try:
        params = {}
        if target_words:
            params["words"] = target_words
            
        response = requests.get(
            f"{YOLO_API_URL}/debug/save_annotated", 
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        return {
            "saved": False,
            "error": "YOLO-E debug API timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "saved": False,
            "error": "Cannot connect to YOLO-E API - is it running?"
        }
    except Exception as e:
        return {
            "saved": False,
            "error": f"YOLO-E debug API error: {str(e)}"
        }

if __name__ == "__main__":
    # Test the YOLO-E tool
    print("Testing YOLO-E Tool...")
    
    # Check health
    health = check_yolo_health()
    print(f"Health: {health}")
    
    # Test current prompts
    current = get_current_prompts()
    print(f"Current prompts: {current}")
    
    # Set new prompts
    print("\nSetting prompts to ['person', 'bottle']...")
    set_result = set_prompts(["person", "bottle"])
    print(f"Set prompts result: {set_result}")
    
    # Test detection with specific prompts
    results = get_yolo_annotations(["person", "car"])
    print(f"Detection results: {results}")
    
    # Test specific object detection
    person_check = scan_for_person()
    print(f"Person detected: {person_check}")
    
    # Test finding specific object
    bottle_result = find_target_object("bottle")
    print(f"Bottle search: {bottle_result}")
    
    # Test debug image saving
    print("\nTesting debug image saving...")
    debug_result = save_debug_image(["person", "bottle", "car"])
    print(f"Debug save result: {debug_result}")
    
    if debug_result.get("saved", False):
        print(f"Saved annotated image to: {debug_result.get('image_path', 'unknown')}")
        print(f"Saved metadata to: {debug_result.get('metadata_path', 'unknown')}")
        print(f"Detected {debug_result.get('detection_count', 0)} objects")
    else:
        print(f"Failed to save debug image: {debug_result.get('error', 'unknown error')}")
    
    # Test debug save with current prompts
    print("\nTesting debug save with current prompts...")
    debug_current = save_debug_image()
    print(f"Debug save (current prompts): {debug_current}")