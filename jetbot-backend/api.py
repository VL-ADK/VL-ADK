# api.py
# FastAPI server for JetBot:
# - Manages HTTP API endpoints for robot control
# - Provides movement commands: forward, backward, left, right, stop

import math
import threading
import time
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jetbot import Robot
from models import RobotControlMessage


class RobotActions:
    """
    Class to control a JetBot robot.
    Provides basic movement functions: forward, backward, left, right, stop.
    """

    def __init__(self, robot):
        self.robot = robot
        self.current_angle = 0
        self.current_coord = {"x": 0, "y": 0}
        self.found_items = []
        self.CALIBRATED_ANGULAR_VELOCITY = 2.3

    def gc_found_items(self, ttl=1000 * 60):
        new_list = []
        for item in self.found_items:
            if int(time.time() * 1000) - item["timestamp_ms"] - ttl < 0:
                new_list.append(item)
        self.found_items = new_list

    # --- Core movement function ---
    def _set_motors(self, left_speed: float, right_speed: float, duration: float, smooth_step: bool = True):
        """
        Set motor speeds and optionally stop after duration.
        """

        self.robot.left_motor.value = left_speed
        self.robot.right_motor.value = right_speed
        if duration is not None:
            if smooth_step:
                # Start slowing down at the last 10% of the duration
                start_slow_down = duration * 0.1
                time.sleep(duration - start_slow_down)

                # Each step will take 1% of a second
                step_time = 0.01
                # Get the number of steps so we take the rest of our duration
                steps = int(start_slow_down / step_time)
                self.smooth_stop(step_time, steps)
            else:
                time.sleep(duration)
                self.stop()

    def scan(self, query: list[str] = [], orientation: Optional[str] = None):
        self.gc_found_items()
        yolo_url = "http://localhost:8001/yolo/"
        params = [("words", word) for word in query]
        if orientation:
            params.append(("orientation", orientation))

        # keep existing behavior
        requests.post(yolo_url + "append-prompts/", params=params)

        # snapshot starting heading (local zero)
        _start_angle = self.current_angle

        total_angle = 360
        turns = 4
        sleep_directive = 3 / turns
        for i in range(turns):
            response = requests.get(yolo_url, params=params)
            resp_json = response.json()
            print(resp_json)
            for annotation in resp_json.get("annotations", []):
                rot = annotation.get("rotation_degree", annotation.get("rotation_deg", 0.0))
                try:
                    rot = float(rot)
                except Exception:
                    rot = 0.0

                # absolute heading at detection time
                _heading_now = self.current_angle + rot
                # angle relative to where the scan started (start treated as 0)
                _angle_from_start = (_heading_now - _start_angle) % 360.0

                self.found_items.append({
                    "item": annotation.get("class"),
                    "seen_at_x": self.current_coord["x"],
                    "seen_at_y": self.current_coord["y"],
                    "angle": _angle_from_start,  # <-- now relative to scan start
                    "timestamp_ms": int(time.time() * 1000)
                })

            self.rotate(total_angle / turns)
            time.sleep(sleep_directive)

        return {
            "x": self.current_coord["x"],
            "y": self.current_coord["y"],
            "angle": (self.current_angle - _start_angle) % 360.0,  # scan end angle relative to start
            "items": self.found_items
        }


    # --- Public movement functions ---
    def move_forward(self, speed: float = 0.5, duration: float = 1):
        self.current_coord = {"x": math.cos(math.radians(self.current_angle)) * (speed * duration), "y": math.sin(math.radians(self.current_angle)) * (speed * duration)}
        self._set_motors(speed, speed, duration)

    def move_backward(self, speed: float = 0.5, duration: float = 1):
        self.current_coord = {"x": math.cos(math.radians(self.current_angle)) * (-speed * duration), "y": math.sin(math.radians(self.current_angle)) * (-speed * duration)}
        self._set_motors(-speed, -speed, duration)

    def rotate(self, angle: float):
        speed = 0.5

        angle_rad = math.radians(angle)
        omega = self.CALIBRATED_ANGULAR_VELOCITY * (speed / 0.5)
        duration = abs(angle_rad / omega)

        # left, right
        left_speed = speed if angle > 0 else -speed
        right_speed = -speed if angle > 0 else speed

        self.current_angle = (((self.current_angle + angle) % 360) + 360) % 360
        self._set_motors(left_speed, right_speed, duration, False)

    def stop(self):
        """
        Stop both motors immediately.
        """
        self.robot.stop()

    def _smooth_decel(self, motor, step_time=0.05, steps=20):
        """Gradually reduce motor speed to 0 in steps."""
        current_speed = motor.value
        for i in range(steps):
            current_speed -= current_speed / (steps - i)
            motor.value = current_speed
            time.sleep(step_time)
        motor.value = 0  # final stop
        self.stop()

    def smooth_stop(self, step_time=0.05, steps=20):
        """Smooth stop both motors in parallel."""
        t1 = threading.Thread(target=self._smooth_decel, args=(self.robot.left_motor, step_time, steps))
        t2 = threading.Thread(target=self._smooth_decel, args=(self.robot.right_motor, step_time, steps))
        t1.start()
        t2.start()
        t1.join()
        t2.join()


class Api:
    def __init__(self, robot: Robot, host: str = "127.0.0.1", port: int = 8890):
        self.host = host
        self.port = port
        self.robot = robot
        self.actions = RobotActions(robot)
        self.app = FastAPI(title="JetBot API")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
            allow_credentials=True,
            allow_methods=["*"],  # GET, POST, OPTIONS, etc.
            allow_headers=["*"],  # Content-Type, Authorization, etc.
        )
        self.server = None
        self.current_command: Optional[RobotControlMessage] = None
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes with the robot actions."""

        # Scan the surrounding area
        @self.app.post("/scan/")
        def api_scan(words: list[str] = [], orientation: Optional[str] = None):
            """
            Scan the environment and return information about detected objects with optional orientation filtering.

            Args:
                words: List of object classes to search for
                orientation: Filter by object orientation ('horizontal' or 'vertical')

            Spatial Reasoning:
                - horizontal: Objects wider than tall (tables, cars, laptops, lying objects)
                - vertical: Objects taller than wide (people, bottles, doors, standing objects)

            Returns:
                x (float): current x position
                y (float): current y position
                angle (float): current angle
                items: A dictionary with the following keys:
                    - item (str): The detected object's class label.
                    - seen_at_x (float): The robot's current x-coordinate when the object was seen.
                    - seen_at_y (float): The robot's current y-coordinate when the object was seen.
                    - angle (float): The robot's orientation angle (in degrees or radians, depending on implementation).
                    - timestamp_ms (int): The Unix timestamp in milliseconds when the object was detected.
                    - object_orientation (str): "horizontal" or "vertical" based on bounding box aspect ratio
                    - aspect_ratio (float): width/height ratio for spatial understanding
            """
            self.current_command = RobotControlMessage(status="scanning")
            data = self.actions.scan(words, orientation)
            return {"status": "scanning", "data": data}

        # Move the robot forward
        @self.app.post("/forward/")
        def api_forward(speed: float = 0.5, duration: float = None):
            print(f"Moving forward at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="moving forward", speed=speed, duration=duration)
            self.actions.move_forward(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "moving forward", "speed": speed, "duration": duration}

        # Move the robot backward
        @self.app.post("/backward/")
        def api_backward(speed: float = 0.5, duration: float = None):
            print(f"Moving backward at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="moving backward", speed=speed, duration=duration)
            self.actions.move_backward(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "moving backward", "speed": speed, "duration": duration}

        # Rotate the robot
        @self.app.post("/rotate/")
        def api_rotate(angle: float):
            print(f"Rotate {angle} degrees")
            self.current_command = RobotControlMessage(status="rotating", angle=angle)
            self.actions.rotate(angle)
            return {"status": "rotating", "angle": angle}

        # Stop the robot
        @self.app.post("/stop/")
        def api_stop():
            print("Stopping robot")
            self.current_command = None
            self.actions.stop()
            return {"status": "stopped"}

    # Start the server
    async def start(self):
        """Start the FastAPI server."""
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info")
        self.server = uvicorn.Server(config)
        print(f"FastAPI server started on {self.host}:{self.port}")
        await self.server.serve()

    # Stop the server
    async def stop(self):
        """Stop the FastAPI server."""
        if self.server:
            self.server.should_exit = True
            print("FastAPI server stopped")
