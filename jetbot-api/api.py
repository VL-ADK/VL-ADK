import subprocess
import time
from jetbot import Robot
from fastapi import FastAPI


# Initialize FastAPI app
app = FastAPI(title="JetBot API")

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

# Initialize robot
robot = Robot(i2c_bus=7, left_motor_channel=1, right_motor_channel=2)
actions = RobotActions(robot)
actions.turn_left(1, 1)

# --- API endpoints ---
@app.post("/forward/")
def api_forward(speed: float = 0.5, duration: float = None):
    actions.move_forward(speed, duration)
    return {"status": "moving forward", "speed": speed, "duration": duration}

@app.post("/backward/")
def api_backward(speed: float = 0.5, duration: float = None):
    actions.move_backward(speed, duration)
    return {"status": "moving backward", "speed": speed, "duration": duration}

@app.post("/left/")
def api_left(speed: float = 0.5, duration: float = None):
    actions.turn_left(speed, duration)
    return {"status": "turning left", "speed": speed, "duration": duration}

@app.post("/right/")
def api_right(speed: float = 0.5, duration: float = None):
    actions.turn_right(speed, duration)
    return {"status": "turning right", "speed": speed, "duration": duration}

@app.post("/stop/")
def api_stop():
    actions.stop()
    return {"status": "stopped"}
