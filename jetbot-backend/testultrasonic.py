import Jetson.GPIO as GPIO
import time

# BCM pin numbers (adjust depending on your wiring)
TRIG = 17
ECHO = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Send 10us pulse to TRIG
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # Wait for ECHO to go HIGH
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    # Wait for ECHO to go LOW
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    # Calculate distance (speed of sound ~34300 cm/s)
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # cm
    return round(distance, 2)

try:
    while True:
        dist = get_distance()
        print(f"Distance: {dist} cm")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Stopped by User")
    GPIO.cleanup()
