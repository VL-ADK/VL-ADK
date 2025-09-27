# main.py
# Main entry point for the JetBot API
# Controls the WebSocket Server for Images and Control Data to the Web App
# Controls the API Controller for operating the JetBot to be used by ADK.

import asyncio
from websocket import WebSocketServer
from models import WebSocketMessage
from jetbot import Camera, bgr8_to_jpeg
import base64
import cv2

# Constants
WEBSOCKET_HOST = "127.0.0.1"
WEBSOCKET_PORT = 8890
IMAGE_WIDTH = 1640
IMAGE_HEIGHT = 1232

# Initialize JetBot Camera with default settings
camera = None
try:
    print("Initializing JetBot Camera with default settings...")
    camera = Camera.instance()
    print("JetBot Camera initialized successfully!")
    
    # Test that we can get a frame
    import time
    time.sleep(1)
    test_frame = camera.value
    if test_frame is not None:
        print(f"Camera working! Frame shape: {test_frame.shape}")
    else:
        print("Camera initialized but no frame yet")
        
except Exception as e:
    print(f"Failed to initialize JetBot Camera: {e}")
    camera = None

async def main():
    # Initialize the WebSocket Server
    websocket_server = WebSocketServer(WEBSOCKET_HOST, WEBSOCKET_PORT)
    await websocket_server.start()

    # Send camera images with control data in a single combined message
    async def send_camera_with_control():
        if camera is None:
            print("No camera available, skipping image streaming")
            return
        
        print("Starting JetBot camera streaming with control data...")
        frame_count = 0
        last_frame_time = 0
        
        while True:
            try:
                if camera is not None and websocket_server.clients:
                    # Only process frames if we have clients
                    current_time = asyncio.get_event_loop().time()
                    
                    # Maintain consistent frame rate
                    if current_time - last_frame_time >= 0.033:  # ~30 FPS
                        # Get BGR frame from JetBot camera
                        bgr_frame = camera.value
                        
                        if bgr_frame is not None:
                            # Convert BGR to JPEG using JetBot's optimized function
                            jpeg_bytes = bgr8_to_jpeg(bgr_frame, quality=80)
                            
                            # Create control data (dummy for now)
                            control_data = WebSocketMessage(left_motor=0.5, right_motor=0.5)
                            
                            # Send image and control data in single message
                            payload = WebSocketMessage(image=jpeg_bytes, left_motor=0.5, right_motor=0.5)
                            await websocket_server.send_websocket_payload(payload)
                            
                            frame_count += 1
                            last_frame_time = current_time
                            
                # Small yield to prevent blocking
                await asyncio.sleep(0.001)  # 1ms yield
            except Exception as e:
                print(f"Error streaming camera: {e}")
                await asyncio.sleep(1)

    # Start the combined camera and control task
    asyncio.create_task(send_camera_with_control())

    # Keep the main function running
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("Shutting down...")
        if camera is not None:
            camera.stop()
            print("JetBot Camera stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted by user")
