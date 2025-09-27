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
API_HOST = "127.0.0.1"
API_PORT = 8001
WEBSOCKET_URL = "ws://localhost:8890"
YOLO_MODEL_PATH = "yoloe-s.pt"

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
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        print(f"Loading YOLO-E model: {YOLO_MODEL_PATH}")
        model = YOLOE(YOLO_MODEL_PATH).to(device)
        print("YOLO-E model loaded successfully!")
    except Exception as e:
        print(f"Failed to load YOLO-E model: {e}")
        model = None

def set_prompts(prompts: List[str]):
    """Set open-vocabulary prompts for YOLO-E."""
    global current_prompts
    if model is None:
        return False
    
    try:
        # Apply open-vocab text prompts to YOLO-E
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
        # Run YOLO-E inference with current prompts
        results = model.predict(
            frame, 
            conf=0.25, 
            iou=0.5, 
            device=device, 
            verbose=False
        )
        
        annotations = []
        if len(results) > 0:
            result = results[0]
            dets = result.boxes
            
            if dets is not None and len(dets) > 0:
                try:
                    # Extract detection data (YOLO-E specific)
                    cls_indices = dets.cls.int().cpu().tolist()
                    confidences = dets.conf.float().cpu().tolist()
                    xyxy_boxes = dets.xyxy.float().cpu().tolist()
                except Exception:
                    # Fallback for older tensor API
                    cls_indices = [int(b.cls) for b in dets]
                    confidences = [float(b.conf) for b in dets]
                    xyxy_boxes = [b.xyxy.float().cpu().numpy().flatten().tolist() for b in dets]
                
                for cls_idx, conf, box in zip(cls_indices, confidences, xyxy_boxes):
                    # YOLO-E: class_id indexes current_prompts, not COCO classes
                    if 0 <= cls_idx < len(current_prompts):
                        class_name = current_prompts[cls_idx]
                    else:
                        class_name = f"unknown_class_{cls_idx}"
                    
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

@app.on_event("startup")
async def startup_event():
    """Initialize YOLO-E model and start WebSocket client on startup."""
    init_yolo()
    # Start WebSocket client in background
    asyncio.create_task(websocket_client())

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)