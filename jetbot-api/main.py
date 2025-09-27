# main.py
# JetBot API entrypoint:
# - Starts WebSocket server for images + control data
# - Starts FastAPI server for robot control
# - Captures frames from JetBot Camera (CSI/USB headless)
# - Streams JPEG frames + control data to web clients

import asyncio
import cv2
from jetbot import Camera, Robot
from websocket import WebSocketServer
from api import Api

# Constants
WEBSOCKET_HOST = "127.0.0.1"
WEBSOCKET_PORT = 8890
API_HOST = "127.0.0.1"
API_PORT = 8889
IMAGE_WIDTH = 1640      
IMAGE_HEIGHT = 1232
TARGET_FPS = 20         
JPEG_QUALITY = 75 

# Initialize JetBot Camera
camera = None
try:
    print("Initializing JetBot Camera...")
    camera = Camera.instance(width=IMAGE_WIDTH, height=IMAGE_HEIGHT)
    import time
    time.sleep(1)  # let camera warm up
    test_frame = camera.value
    if test_frame is not None:
        print(f"✅ Camera working! Frame shape: {test_frame.shape}")
    else:
        print("⚠️ Camera initialized but no frame yet")
except Exception as e:
    print(f"❌ Failed to initialize JetBot Camera: {e}")
    camera = None

# Initialize JetBot Robot
robot = None
try:
    print("Initializing JetBot Robot...")
    robot = Robot(i2c_bus=7, left_motor_channel=1, right_motor_channel=2)
    print("✅ Robot initialized successfully!")
except Exception as e:
    print(f"❌ Failed to initialize JetBot Robot: {e}")
    robot = None


async def main():
    # Initialize servers
    websocket_server = WebSocketServer(WEBSOCKET_HOST, WEBSOCKET_PORT)
    await websocket_server.start()
    
    # Initialize API server if robot is available
    api_server = None
    if robot is not None:
        api_server = Api(robot, API_HOST, API_PORT)
        asyncio.create_task(api_server.start())
    else:
        print("⚠️ Skipping API server - no robot available")

    async def stream_camera():
        if camera is None:
            print("No camera available, skipping image streaming")
            return

        print("Starting JetBot camera streaming...")
        frame_period = 1.0 / TARGET_FPS
        next_t = asyncio.get_event_loop().time()

        while True:
            try:
                now = asyncio.get_event_loop().time()
                if now < next_t:
                    await asyncio.sleep(next_t - now)
                next_t += frame_period

                if not websocket_server.clients:
                    # still grab a frame to keep pipeline alive
                    _ = camera.value
                    continue

                frame = camera.value
                if frame is None:
                    continue

                # Encode JPEG off the main loop
                ok, buf = await asyncio.to_thread(
                    cv2.imencode, ".jpg", frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                )
                if not ok:
                    continue

                # Get current robot command from API server
                current_control = api_server.current_command if api_server else None
                
                await websocket_server.broadcast_payload(
                    buf.tobytes(),
                    left_motor=robot.left_motor.value if robot else 0.0,
                    right_motor=robot.right_motor.value if robot else 0.0,
                    control=current_control
                )
            except Exception as e:
                print(f"[stream] error: {e}")
                await asyncio.sleep(0.1)

    asyncio.create_task(stream_camera())

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("Shutting down...")
        if camera is not None:
            camera.stop()
            print("Camera stopped")
        if api_server is not None:
            await api_server.stop()
        await websocket_server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted by user")
