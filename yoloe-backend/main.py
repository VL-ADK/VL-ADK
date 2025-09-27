import websockets
import asyncio
import json
import base64
import numpy as np
from fastapi import FastAPI, Query
from typing import List, Optional
import uvicorn
import time
from threading import Lock

# Import OpenCV with fallback
try:
    import cv2
    print("OpenCV imported successfully")
except ImportError as e:
    print(f"OpenCV import failed: {e}")
    print("Please ensure system OpenCV is installed: sudo apt install python3-opencv")
    raise

# Import PyTorch with fallback
try:
    import torch
    print(f"PyTorch imported successfully (device: {'cuda' if torch.cuda.is_available() else 'cpu'})")
except ImportError as e:
    print(f"PyTorch import failed: {e}")
    print("Please install PyTorch for Jetson or run setup_dependencies.sh")
    raise

# Import YOLO-E with fallback
try:
    from ultralytics import YOLOE
    print("YOLO-E imported successfully")
except ImportError as e:
    print(f"YOLO-E import failed: {e}")
    print("Please install ultralytics: pip install ultralytics>=8.0.196")
    raise

# Configuration
import os
from datetime import datetime
API_HOST = "127.0.0.1"
API_PORT = 8001
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8890")
YOLO_MODEL_PATH = "yoloe-l.pt"
FORCE_CPU = os.getenv("FORCE_CPU", "false").lower() == "true"
DEBUG_SAVE_DIR = os.getenv("DEBUG_SAVE_DIR", "./debug_images")

# Create debug directory if it doesn't exist
os.makedirs(DEBUG_SAVE_DIR, exist_ok=True)

# Initialize FastAPI
app = FastAPI(title="YOLOE Backend", description="YOLO Object Detection for VL-ADK", version="0.1.0")

# Global variables for image streaming
latest_frame = None
frame_lock = Lock()
model = None
current_prompts = []  # Track current open-vocab prompts
device = None

# Initialize YOLO-E model
def init_yolo():
    global model, device
    try:
        # Force CPU if environment variable is set or CUDA has issues
        if FORCE_CPU:
            device = "cpu"
            print("Forcing CPU mode due to FORCE_CPU=true")
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Using device: {device}")
        print(f"Loading YOLO-E model: {YOLO_MODEL_PATH}")
        
        # Try to load model, fallback to CPU if CUDA fails
        try:
            model = YOLOE(YOLO_MODEL_PATH).to(device)
        except RuntimeError as cuda_error:
            if "CUDA" in str(cuda_error) and device == "cuda":
                print(f"CUDA error encountered: {cuda_error}")
                print("Falling back to CPU mode...")
                device = "cpu"
                model = YOLOE(YOLO_MODEL_PATH).to(device)
            else:
                raise
        
        print("YOLO-E model loaded successfully!")
    except Exception as e:
        print(f"Failed to load YOLO-E model: {e}")
        model = None

def set_prompts(prompts: List[str]):
    """Set open-vocabulary prompts for YOLO-E (matching working example)."""
    global current_prompts
    if model is None:
        return False
    
    try:
        # Apply open-vocab text prompts to YOLO-E (exact same as working example)
        try:
            pe = model.get_text_pe(prompts)  # text positional encodings (if available)
            model.set_classes(prompts, pe)
        except Exception:
            # Fallback: some builds expose only set_classes(names)
            model.set_classes(prompts)
        
        current_prompts = prompts.copy()
        print(f"Set YOLO-E prompts to: {prompts}")
        return True
    except Exception as e:
        print(f"Failed to set prompts: {e}")
        return False

def draw_annotations_on_frame(frame, annotations, save_path=None):
    """Draw bounding boxes and labels on frame, optionally save to file."""
    if frame is None or not annotations:
        return frame
    
    # Create a copy to avoid modifying original
    annotated_frame = frame.copy()
    
    # Define colors for different classes (BGR format)
    colors = [
        (0, 255, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 0, 255),    # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
        (128, 0, 128),  # Purple
        (255, 165, 0),  # Orange
    ]
    
    for i, ann in enumerate(annotations):
        # Get bounding box coordinates
        x1, y1, x2, y2 = ann["bbox"]
        
        # Choose color based on class
        color_idx = ann.get("prompt_index", i) % len(colors)
        color = colors[color_idx]
        
        # Draw bounding box
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
        
        # Prepare label text
        class_name = ann["class"]
        confidence = ann["confidence"]
        label = f"{class_name}: {confidence:.2f}"
        
        # Get text size for background
        (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        
        # Draw label background
        cv2.rectangle(annotated_frame, 
                     (x1, y1 - text_height - 10), 
                     (x1 + text_width, y1), 
                     color, -1)
        
        # Draw label text
        cv2.putText(annotated_frame, label, 
                   (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   (255, 255, 255), 2)
        
        # Draw center point
        center_x, center_y = int(ann["center"][0]), int(ann["center"][1])
        cv2.circle(annotated_frame, (center_x, center_y), 4, color, -1)
    
    # Save to file if path provided
    if save_path:
        cv2.imwrite(save_path, annotated_frame)
        print(f"Saved annotated image to: {save_path}")
    
    return annotated_frame

# WebSocket client to receive images
async def websocket_client():
    global latest_frame
    
    while True:
        try:
            print(f"Connecting to WebSocket: {WEBSOCKET_URL}")
            async with websockets.connect(WEBSOCKET_URL) as ws:
                print("Connected to JetBot WebSocket")
                
                async for message in ws:
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
                            
                            # Store latest frame thread-safely
                            with frame_lock:
                                latest_frame = {
                                    "frame": frame,
                                    "timestamp": time.time(),
                                    "motor_data": {
                                        "left_motor": data.get("left_motor", 0.0),
                                        "right_motor": data.get("right_motor", 0.0)
                                    }
                                }
                                
                    except Exception as e:
                        print(f"Error processing WebSocket message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed, retrying in 3 seconds...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"WebSocket error: {e}, retrying in 5 seconds...")
            await asyncio.sleep(5)

def run_yolo_detection(frame, target_words: List[str] = None):
    """Run YOLO-E detection on frame with open-vocabulary prompts."""
    global current_prompts
    
    if model is None:
        return {"error": "YOLO-E model not loaded"}
    
    # Set prompts if target_words provided and different from current
    if target_words and target_words != current_prompts:
        if not set_prompts(target_words):
            return {"error": "Failed to set YOLO-E prompts"}
    elif not target_words and not current_prompts:
        # Default prompts if none set
        default_prompts = ["person", "car", "bottle", "chair", "dog", "cat"]
        if not set_prompts(default_prompts):
            return {"error": "Failed to set default prompts"}
    
    try:
        # Run YOLO-E inference with current prompts (exact same as working example)
        results = model.predict(
            frame, 
            conf=0.25,  # Same as working example
            iou=0.5,    # Same as working example
            device=device, 
            verbose=False
        )
        
        annotations = []
        if len(results) > 0:
            result = results[0]
            dets = result.boxes
            
            # Debug output (like working example)
            if dets is not None and len(dets) > 0:
                n = len(dets)
                try:
                    # Extract detection data (exact same as working example)
                    cls_indices = dets.cls.int().cpu().tolist()
                    confidences = dets.conf.float().cpu().tolist()
                    xyxy_boxes = dets.xyxy.int().cpu().tolist()  # Note: int() like working example
                except Exception:
                    # Fallback for older tensor API (same as working example)
                    cls_indices = []
                    confidences = []
                    xyxy_boxes = []
                    for b in dets:
                        cls_indices.append(int(b.cls))
                        confidences.append(float(b.conf))
                        xyxy_boxes.append(b.xyxy.int().cpu().numpy().flatten().tolist())
                
                print(f"[DEBUG] {n} detections for prompts {current_prompts}")
                
                for i, (cls_idx, conf, box) in enumerate(zip(cls_indices, confidences, xyxy_boxes)):
                    # YOLO-E: class_id indexes current_prompts, not COCO classes (same as working example)
                    if 0 <= cls_idx < len(current_prompts):
                        class_name = current_prompts[cls_idx]
                    else:
                        class_name = f"id{cls_idx}"  # Same format as working example
                    
                    print(f"   {i}: {class_name} {conf:.2f} at {box}")  # Debug output like working example
                    
                    x1, y1, x2, y2 = box
                    
                    annotation = {
                        "class": class_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "center": [(x1 + x2) / 2, (y1 + y2) / 2],
                        "area": (x2 - x1) * (y2 - y1),
                        "prompt_index": cls_idx
                    }
                    annotations.append(annotation)
            else:
                print(f"[DEBUG] 0 detections for prompts {current_prompts}")  # Debug output like working example
        
        return {
            "annotations": annotations,
            "count": len(annotations),
            "timestamp": time.time(),
            "image_shape": frame.shape if frame is not None else None,
            "current_prompts": current_prompts.copy(),
            "model_type": "YOLO-E"
        }
        
    except Exception as e:
        return {"error": f"YOLO-E detection failed: {str(e)}"}

@app.get("/yolo/")
async def get_yolo_annotations(words: Optional[List[str]] = Query(None, description="Target words to detect")):
    """Get YOLO object detection results, optionally filtered by target words."""
    
    with frame_lock:
        if latest_frame is None:
            return {
                "error": "No image available from WebSocket stream",
                "annotations": [],
                "count": 0
            }
        
        frame_data = latest_frame.copy()
    
    # Check if frame is too old (>5 seconds)
    if time.time() - frame_data["timestamp"] > 5:
        return {
            "error": "Image data is stale",
            "annotations": [],
            "count": 0,
            "age_seconds": time.time() - frame_data["timestamp"]
        }
    
    # Run YOLO detection
    results = run_yolo_detection(frame_data["frame"], words)
    
    # Add metadata
    results["motor_data"] = frame_data["motor_data"]
    results["frame_timestamp"] = frame_data["timestamp"]
    results["detection_timestamp"] = time.time()
    
    return results

@app.post("/prompts/")
async def set_detection_prompts(prompts: List[str]):
    """Set new open-vocabulary prompts for YOLO-E detection."""
    if not prompts:
        return {"error": "Empty prompts list"}
    
    success = set_prompts(prompts)
    return {
        "success": success,
        "current_prompts": current_prompts.copy(),
        "message": f"Prompts set to: {prompts}" if success else "Failed to set prompts"
    }

@app.get("/prompts/")
async def get_current_prompts():
    """Get currently active prompts."""
    return {
        "current_prompts": current_prompts.copy(),
        "model_loaded": model is not None,
        "device": device
    }

@app.get("/health/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_type": "YOLO-E",
        "current_prompts": current_prompts.copy(),
        "device": device,
        "latest_frame_age": time.time() - latest_frame["timestamp"] if latest_frame else None,
        "websocket_connected": latest_frame is not None
    }

@app.get("/debug/save_annotated")
async def save_annotated_image(words: Optional[List[str]] = Query(None, description="Target words to detect")):
    """Save current frame with YOLO annotations to debug directory on laptop."""
    
    with frame_lock:
        if latest_frame is None:
            return {
                "error": "No image available from WebSocket stream",
                "saved": False
            }
        
        frame_data = latest_frame.copy()
    
    # Check if frame is too old
    if time.time() - frame_data["timestamp"] > 5:
        return {
            "error": "Image data is stale",
            "saved": False,
            "age_seconds": time.time() - frame_data["timestamp"]
        }
    
    # Run YOLO detection
    results = run_yolo_detection(frame_data["frame"], words)
    
    if "error" in results:
        return {
            "error": results["error"],
            "saved": False
        }
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompts_str = "_".join(words) if words else "_".join(current_prompts) if current_prompts else "default"
    filename = f"yolo_debug_{timestamp}_{prompts_str}.jpg"
    save_path = os.path.join(DEBUG_SAVE_DIR, filename)
    
    # Draw annotations and save
    annotated_frame = draw_annotations_on_frame(frame_data["frame"], results["annotations"], save_path)
    
    # Also save metadata
    metadata_path = save_path.replace(".jpg", "_metadata.json")
    metadata = {
        "timestamp": timestamp,
        "prompts": results.get("current_prompts", []),
        "detection_count": results.get("count", 0),
        "annotations": results["annotations"],
        "motor_data": frame_data["motor_data"],
        "frame_timestamp": frame_data["timestamp"],
        "detection_timestamp": time.time(),
        "image_shape": results.get("image_shape", None)
    }
    
    with open(metadata_path, 'w') as f:
        import json
        json.dump(metadata, f, indent=2)
    
    return {
        "saved": True,
        "image_path": save_path,
        "metadata_path": metadata_path,
        "detection_count": results.get("count", 0),
        "prompts": results.get("current_prompts", []),
        "annotations": results["annotations"]
    }

@app.on_event("startup")
async def startup_event():
    """Initialize YOLO-E model and start WebSocket client on startup."""
    init_yolo()
    # Start WebSocket client in background
    asyncio.create_task(websocket_client())

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)