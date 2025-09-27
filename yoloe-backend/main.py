# yolo_main.py
# YOLO-E Backend entrypoint:
# - Starts WebSocket server for annotated images + detection data (port 8002)
# - Starts FastAPI server for YOLO detection API (port 8001)
# - Receives frames from JetBot WebSocket
# - Runs YOLO-E detection and streams annotated results

import asyncio
import cv2
import json
import base64
import numpy as np
import websockets
import time
import os
from websocket import YoloWebSocketServer
from api import YoloApi
from model import YoloModelManager

# Constants
WEBSOCKET_HOST = "127.0.0.1"
WEBSOCKET_PORT = 8002
API_HOST = "127.0.0.1"
API_PORT = 8001
JETBOT_WEBSOCKET_URL = "ws://localhost:8890"
YOLO_MODEL_PATH = "yoloe-l.pt"
FORCE_CPU = os.getenv("FORCE_CPU", "false").lower() == "true"
TARGET_FPS = 20

# Import checks
try:
    import torch
    print(f"PyTorch imported successfully (device: {'cuda' if torch.cuda.is_available() else 'cpu'})")
except ImportError as e:
    print(f"PyTorch import failed: {e}")
    raise

try:
    print("OpenCV imported successfully")
except ImportError as e:
    print(f"OpenCV import failed: {e}")
    raise

# Initialize YOLO Model Manager
model_manager = None
try:
    print("Initializing YOLO-E Model Manager...")
    model_manager = YoloModelManager(YOLO_MODEL_PATH, FORCE_CPU)
    if model_manager.model is not None:
        print("YOLO-E Model Manager initialized successfully!")
    else:
        print("YOLO-E Model Manager failed to load model")
except Exception as e:
    print(f"Failed to initialize YOLO-E Model Manager: {e}")
    model_manager = None

async def main():
    # Initialize servers
    websocket_server = YoloWebSocketServer(WEBSOCKET_HOST, WEBSOCKET_PORT)
    await websocket_server.start()
    
    # Initialize API server if model is available
    api_server = None
    if model_manager is not None:
        api_server = YoloApi(model_manager, API_HOST, API_PORT)
        asyncio.create_task(api_server.start())
    else:
        print("Skipping API server - no YOLO model available")

    async def jetbot_websocket_client():
        """Connect to JetBot WebSocket and receive frames."""
        if model_manager is None:
            print("No model manager available, skipping JetBot WebSocket client")
            return

        while True:
            try:
                print(f"Connecting to JetBot WebSocket: {JETBOT_WEBSOCKET_URL}")
                async with websockets.connect(JETBOT_WEBSOCKET_URL) as ws:
                    print("Connected to JetBot WebSocket")
                    
                    async for message in ws:
                        try:
                            # Parse JSON message from JetBot
                            data = json.loads(message)
                            
                            # Extract base64 image
                            if "image" in data:
                                image_b64 = data["image"]
                                
                                # Decode base64 to bytes
                                image_bytes = base64.b64decode(image_b64)
                                
                                # Convert to numpy array
                                nparr = np.frombuffer(image_bytes, np.uint8)
                                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                
                                # Update model manager with latest frame
                                motor_data = {
                                    "left_motor": data.get("left_motor", 0.0),
                                    "right_motor": data.get("right_motor", 0.0)
                                }
                                model_manager.update_frame(frame, time.time(), motor_data)
                                
                        except Exception as e:
                            print(f"Error processing JetBot WebSocket message: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                print("JetBot WebSocket connection closed, retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"JetBot WebSocket error: {e}, retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def stream_annotated_frames():
        """Stream annotated frames to WebSocket clients."""
        if model_manager is None:
            print("No model manager available, skipping annotated frame streaming")
            return

        print("Starting YOLO-E annotated frame streaming...")
        frame_period = 1.0 / TARGET_FPS
        next_t = asyncio.get_event_loop().time()

        while True:
            try:
                now = asyncio.get_event_loop().time()
                if now < next_t:
                    await asyncio.sleep(next_t - now)
                next_t += frame_period

                if not websocket_server.clients:
                    # No clients connected, skip processing
                    continue

                # Get latest frame
                frame_data = model_manager.get_latest_frame()
                if not frame_data:
                    continue

                frame = frame_data["frame"]
                if frame is None:
                    continue

                # Run YOLO detection on frame
                detection_results = model_manager.run_detection(frame)
                
                if "error" in detection_results:
                    print(f"Detection error: {detection_results['error']}")
                    continue

                # Draw annotations on frame
                annotated_frame = model_manager.draw_annotations_on_frame(
                    frame, 
                    detection_results["annotations"]
                )

                # Encode annotated frame as JPEG
                ok, buf = await asyncio.to_thread(
                    cv2.imencode, ".jpg", annotated_frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 75]
                )
                if not ok:
                    continue

                # Prepare detection data for WebSocket
                detection_data = {
                    "timestamp": detection_results["timestamp"],
                    "current_prompts": detection_results["current_prompts"],
                    "motor_data": frame_data["motor_data"],
                    "frame_timestamp": frame_data["timestamp"],
                    "detection_timestamp": detection_results["timestamp"],
                    "image_shape": detection_results.get("image_shape")
                }

                # Broadcast annotated frame + detection data
                await websocket_server.broadcast_annotated_frame(
                    buf.tobytes(),
                    detection_results["annotations"],
                    detection_data
                )
                
            except Exception as e:
                print(f"[annotated_stream] error: {e}")
                await asyncio.sleep(0.1)

    # Start background tasks
    asyncio.create_task(jetbot_websocket_client())
    asyncio.create_task(stream_annotated_frames())

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("Shutting down...")
        if api_server is not None:
            await api_server.stop()
        await websocket_server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted by user")