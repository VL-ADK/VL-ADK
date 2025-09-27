"""
YOLO-E Tool for ADK Agents
Provides a simple interface for agents to get object detection results using YOLO-E open-vocabulary capabilities.
"""

import requests
from typing import List, Dict, Optional
import time
import subprocess
import json
import cv2
import numpy as np
import base64
import asyncio
import websockets
import threading

YOLO_API_URL = "http://localhost:8001"
YOLO_WEBSOCKET_URL = "ws://localhost:8002"

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

def run_curl_command(url: str, method: str = "GET", params: Dict = None) -> Dict:
    """Run a curl command and return the JSON response."""
    try:
        # Build curl command
        curl_cmd = ["curl", "-s"]
        
        if method.upper() == "POST":
            curl_cmd.extend(["-X", "POST"])
            if params:
                curl_cmd.extend(["-H", "Content-Type: application/json"])
                curl_cmd.extend(["-d", json.dumps(params)])
        elif params:
            # GET with query parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        curl_cmd.append(url)
        
        print(f"Running curl: {' '.join(curl_cmd)}")
        
        # Execute curl
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response", "raw_output": result.stdout}
        else:
            return {"error": f"Curl failed: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"error": "Curl command timed out"}
    except Exception as e:
        return {"error": f"Curl error: {str(e)}"}

def test_curl_endpoints():
    """Test all endpoints using curl commands."""
    print("\n" + "="*50)
    print("TESTING ENDPOINTS WITH CURL")
    print("="*50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    health = run_curl_command(f"{YOLO_API_URL}/health/")
    print(f"Health: {health}")
    
    # Test get prompts
    print("\n2. Testing get prompts...")
    prompts = run_curl_command(f"{YOLO_API_URL}/prompts/")
    print(f"Current prompts: {prompts}")
    
    # Test set prompts
    print("\n3. Testing set prompts...")
    set_prompts_result = run_curl_command(
        f"{YOLO_API_URL}/prompts/", 
        method="POST", 
        params=["person", "bottle", "car"]
    )
    print(f"Set prompts result: {set_prompts_result}")
    
    # Test detection
    print("\n4. Testing detection...")
    detection = run_curl_command(
        f"{YOLO_API_URL}/yolo/", 
        params={"words": "person", "words": "bottle"}
    )
    print(f"Detection result: {detection}")
    
    # Test debug save
    print("\n5. Testing debug save...")
    debug_save = run_curl_command(
        f"{YOLO_API_URL}/debug/save_annotated", 
        params={"words": "person"}
    )
    print(f"Debug save result: {debug_save}")

class WebSocketViewer:
    """Class to handle WebSocket connection and display annotated frames."""
    
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.running = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.base_prompts = ["person", "bottle", "car", "chair"]  # Base set of prompts
        self.current_removed_word_index = -1  # -1 means no word removed
        self.last_prompt_change = time.time()
        self.prompt_change_interval = 3.0  # 3 seconds
    
    def _cycle_prompts(self):
        """Cycle through removing words from prompts."""
        current_time = time.time()
        
        # Check if it's time to change prompts
        if current_time - self.last_prompt_change >= self.prompt_change_interval:
            self.last_prompt_change = current_time
            
            # Cycle to next word to remove
            self.current_removed_word_index += 1
            
            # If we've cycled through all words, start over with no word removed
            if self.current_removed_word_index >= len(self.base_prompts):
                self.current_removed_word_index = -1
            
            # Build current prompts (remove one word if index is valid)
            if self.current_removed_word_index == -1:
                current_prompts = self.base_prompts.copy()
                action = "Added all words back"
            else:
                current_prompts = [word for i, word in enumerate(self.base_prompts) 
                                 if i != self.current_removed_word_index]
                removed_word = self.base_prompts[self.current_removed_word_index]
                action = f"Removed '{removed_word}'"
            
            # Update prompts via API
            try:
                result = set_prompts(current_prompts)
                if result.get("success", False):
                    print(f"Prompt change: {action}")
                    print(f"   Current prompts: {current_prompts}")
                else:
                    print(f"Failed to update prompts: {result.get('message', 'Unknown error')}")
            except Exception as e:
                print(f"Error updating prompts: {e}")
        
    def start_viewer(self):
        """Start the WebSocket viewer in a separate thread."""
        self.running = True
        websocket_thread = threading.Thread(target=self._websocket_worker)
        websocket_thread.daemon = True
        websocket_thread.start()
        
        # Start CV2 display loop
        self._display_loop()
    
    def _websocket_worker(self):
        """WebSocket client worker (runs in separate thread)."""
        def run_websocket_client():
            async def websocket_client():
                try:
                    print(f"Connecting to WebSocket: {self.websocket_url}")
                    async with websockets.connect(self.websocket_url) as ws:
                        print("Connected to YOLO WebSocket stream")
                        
                        async for message in ws:
                            if not self.running:
                                break
                                
                            try:
                                # Parse JSON message
                                data = json.loads(message)
                                
                                # Extract base64 image
                                if "image" in data:
                                    image_b64 = data["image"]
                                    
                                    # Decode base64 to bytes
                                    image_bytes = base64.b64decode(image_b64)
                                    
                                    # Convert to numpy array
                                    nparr = np.frombuffer(image_bytes, np.uint8)
                                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                    
                                    # Update latest frame thread-safely
                                    with self.frame_lock:
                                        self.latest_frame = {
                                            "frame": frame,
                                            "annotations": data.get("annotations", []),
                                            "detection_count": data.get("detection_count", 0),
                                            "current_prompts": data.get("current_prompts", []),
                                            "timestamp": data.get("timestamp")
                                        }
                                        
                            except Exception as e:
                                print(f"Error processing WebSocket message: {e}")
                                
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                except Exception as e:
                    print(f"WebSocket error: {e}")
            
            # Run the async function
            asyncio.run(websocket_client())
        
        run_websocket_client()
    
    def _display_loop(self):
        """Display loop for CV2 window."""
        print("Starting CV2 display window...")
        print("Press 'q' to quit, 's' to save current frame")
        
        cv2.namedWindow("YOLO-E Annotated Stream", cv2.WINDOW_AUTOSIZE)
        
        frame_count = 0
        last_detection_count = 0
        
        # Set initial prompts
        print("Setting initial prompts...")
        initial_result = set_prompts(self.base_prompts)
        if initial_result.get("success", False):
            print(f"Initial prompts set: {self.base_prompts}")
        else:
            print(f"Failed to set initial prompts: {initial_result.get('message', 'Unknown error')}")
        
        while self.running:
            # Cycle prompts every 3 seconds
            self._cycle_prompts()
            
            with self.frame_lock:
                frame_data = self.latest_frame
            
            if frame_data is not None:
                frame = frame_data["frame"]
                annotations = frame_data["annotations"]
                detection_count = frame_data["detection_count"]
                prompts = frame_data["current_prompts"]
                
                if frame is not None:
                    # Add overlay text with detection info
                    display_frame = frame.copy()
                    
                    # Add text overlay
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.7
                    color = (0, 255, 0)  # Green
                    thickness = 2
                    
                    # Detection count
                    text = f"Detections: {detection_count}"
                    cv2.putText(display_frame, text, (10, 30), font, font_scale, color, thickness)
                    
                    # Current prompts
                    prompts_text = f"Prompts: {', '.join(prompts) if prompts else 'None'}"
                    cv2.putText(display_frame, prompts_text, (10, 60), font, font_scale, color, thickness)
                    
                    # Frame counter
                    frame_count += 1
                    frame_text = f"Frame: {frame_count}"
                    cv2.putText(display_frame, frame_text, (10, 90), font, font_scale, color, thickness)
                    
                    # Show detection count change
                    if detection_count != last_detection_count:
                        print(f"Detection count changed: {last_detection_count} -> {detection_count}")
                        if annotations:
                            for i, ann in enumerate(annotations):
                                print(f"  {i+1}. {ann['class']} ({ann['confidence']:.2f})")
                        last_detection_count = detection_count
                    
                    # Display frame
                    cv2.imshow("YOLO-E Annotated Stream", display_frame)
            else:
                # Show placeholder when no frame available
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Waiting for WebSocket stream...", 
                           (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow("YOLO-E Annotated Stream", placeholder)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quit requested by user")
                break
            elif key == ord('s') and frame_data is not None:
                # Save current frame
                timestamp = int(time.time())
                filename = f"yolo_viewer_capture_{timestamp}.jpg"
                cv2.imwrite(filename, frame_data["frame"])
                print(f"Saved frame to: {filename}")
        
        self.running = False
        cv2.destroyAllWindows()
        print("CV2 window closed")

def start_websocket_viewer():
    """Start the WebSocket viewer."""
    print("\n" + "="*50)
    print("STARTING WEBSOCKET VIEWER WITH PROMPT CYCLING")
    print("="*50)
    print("This will open a CV2 window showing the annotated stream")
    print("Prompts will cycle every 3 seconds:")
    print("   - Start: All prompts ['person', 'bottle', 'car', 'chair']")
    print("   - Remove 'person' for 3s")
    print("   - Add back 'person', remove 'bottle' for 3s") 
    print("   - Add back 'bottle', remove 'car' for 3s")
    print("   - Add back 'car', remove 'chair' for 3s")
    print("   - Add back 'chair' (full cycle complete)")
    print("   - Repeat cycle...")
    print("")
    print("Controls:")
    print("  Press 'q' to quit")
    print("  Press 's' to save current frame")
    
    viewer = WebSocketViewer(YOLO_WEBSOCKET_URL)
    viewer.start_viewer()

if __name__ == "__main__":
    print("YOLO-E Testing Suite")
    print("=" * 60)
    print("Choose test mode:")
    print("1. Standard API tests (requests)")
    print("2. Curl command tests") 
    print("3. WebSocket viewer (CV2 window)")
    print("4. All tests + viewer")
    print("5. Just viewer (skip API tests)")
    
    try:
        choice = input("\nEnter choice (1-5): ").strip()
    except KeyboardInterrupt:
        print("\nExiting...")
        exit(0)
    
    if choice in ["1", "4"]:
        # Standard API tests
        print("\n" + "="*50)
        print("STANDARD API TESTS")
        print("="*50)
        
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
    
    if choice in ["2", "4"]:
        # Curl tests
        test_curl_endpoints()
    
    if choice in ["3", "4", "5"]:
        # WebSocket viewer
        if choice == "4":
            print(f"\nStarting WebSocket viewer in 3 seconds...")
            time.sleep(3)
        start_websocket_viewer()
    
    print("\nTesting complete!")