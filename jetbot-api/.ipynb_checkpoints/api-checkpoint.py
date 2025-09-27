from jetbot import Robot
import time

robot.left_motor.value = -0.5
robot.right_motor.value = -0.5
time.sleep(1)
robot.stop()