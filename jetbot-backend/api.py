# api.py
# FastAPI server for JetBot:
# - Manages HTTP API endpoints for robot control
# - Provides movement commands: forward, backward, left, right, stop

import time
import uvicorn
import threading
from typing import Optional
from fastapi import FastAPI
from jetbot import Robot
from models import RobotControlMessage
import math

class RobotActions:
    """
    Class to control a JetBot robot.
    Provides basic movement functions: forward, backward, left, right, stop.
    """
    def __init__(self, robot):
        self.robot = robot
        self.CALIBRATED_ANGULAR_VELOCITY = 2.6

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
                start_slow_down = (duration*0.1)
                time.sleep(duration-start_slow_down)

                # Each step will take 1% of a second
                step_time = 0.01
                # Get the number of steps so we take the rest of our duration
                steps = int(start_slow_down/step_time)
                self.smooth_stop(step_time, steps)
            else:
                time.sleep(duration)
                self.stop()

    def scan(self):
        total_angle = 360
        turns = 4
        sleep_directive = 1/turns
        for i in range(turns):
            self.rotate(total_angle/turns)
            time.sleep(sleep_directive)

    # --- Public movement functions ---
    def move_forward(self, speed: float = 0.5, duration: float = None):
        self._set_motors(speed, speed, duration)

    def move_backward(self, speed: float = 0.5, duration: float = None):
        self._set_motors(-speed, -speed, duration)

    def rotate(self, angle: float):
        speed = 0.5

        angle_rad = math.radians(angle)
        print(angle_rad)
        omega = self.CALIBRATED_ANGULAR_VELOCITY*(speed/0.5)
        duration = abs(angle_rad / omega)

        # left, right
        left_speed = speed if angle > 0 else -speed
        right_speed = -speed if angle > 0 else speed

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
        self.server = None
        self.current_command: Optional[RobotControlMessage] = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all API routes with the robot actions."""

        # Scan the surrounding area
        @self.app.post("/scan/")
        def api_scan():
            self.current_command = RobotControlMessage(status="scanning")
            self.actions.scan()
            return {"status": "scanning"}

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
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        self.server = uvicorn.Server(config)
        print(f"FastAPI server started on {self.host}:{self.port}")
        await self.server.serve()
    
    # Stop the server
    async def stop(self):
        """Stop the FastAPI server."""
        if self.server:
            self.server.should_exit = True
            print("FastAPI server stopped")
