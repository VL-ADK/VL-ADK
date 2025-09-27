# api.py
# FastAPI server for JetBot:
# - Manages HTTP API endpoints for robot control
# - Provides movement commands: forward, backward, left, right, stop

import time
import uvicorn
from typing import Optional
from fastapi import FastAPI
from jetbot import Robot
from models import RobotControlMessage


class RobotActions:
    """
    Class to control a JetBot robot.
    Provides basic movement functions: forward, backward, left, right, stop.
    """
    def __init__(self, robot):
        self.robot = robot

    # --- Core movement function ---
    def _set_motors(self, left_speed: float, right_speed: float, duration: float = 1):
        """
        Set motor speeds and optionally stop after duration.
        """
        self.robot.left_motor.value = left_speed
        self.robot.right_motor.value = right_speed
        if duration is not None:
            time.sleep(duration)
            self.stop()

    # --- Public movement functions ---
    def move_forward(self, speed: float = 0.5, duration: float = None):
        self._set_motors(speed, speed, duration)

    def move_backward(self, speed: float = 0.5, duration: float = None):
        self._set_motors(-speed, -speed, duration)

    def turn_left(self, speed: float = 0.5, duration: float = None):
        self._set_motors(-speed, speed, duration)

    def turn_right(self, speed: float = 0.5, duration: float = None):
        self._set_motors(speed, -speed, duration)

    def stop(self):
        """
        Stop both motors immediately.
        """
        self.robot.stop()


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
        @self.app.post("/forward/")
        def api_forward(speed: float = 0.5, duration: float = None):
            print(f"Moving forward at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="moving forward", speed=speed, duration=duration)
            self.actions.move_forward(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "moving forward", "speed": speed, "duration": duration}

        @self.app.post("/backward/")
        def api_backward(speed: float = 0.5, duration: float = None):
            print(f"Moving backward at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="moving backward", speed=speed, duration=duration)
            self.actions.move_backward(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "moving backward", "speed": speed, "duration": duration}

        @self.app.post("/left/")
        def api_left(speed: float = 0.5, duration: float = None):
            print(f"Turning left at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="turning left", speed=speed, duration=duration)
            self.actions.turn_left(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "turning left", "speed": speed, "duration": duration}

        @self.app.post("/right/")
        def api_right(speed: float = 0.5, duration: float = None):
            print(f"Turning right at speed {speed} for {duration} seconds")
            self.current_command = RobotControlMessage(status="turning right", speed=speed, duration=duration)
            self.actions.turn_right(speed, duration)
            if duration is not None:
                self.current_command = None
            return {"status": "turning right", "speed": speed, "duration": duration}

        @self.app.post("/stop/")
        def api_stop():
            print("Stopping robot")
            self.current_command = None
            self.actions.stop()
            return {"status": "stopped"}
    
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
    
    async def stop(self):
        """Stop the FastAPI server."""
        if self.server:
            self.server.should_exit = True
            print("FastAPI server stopped")
