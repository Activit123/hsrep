#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# --- Pin configuration (modify as needed) ---
FORWARD_PIN = 18   # GPIO pin that drives the forward branch of the H-bridge
REVERSE_PIN = 23   # GPIO pin that drives the reverse branch of the H-bridge

# --- Setup GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(FORWARD_PIN, GPIO.OUT)
GPIO.setup(REVERSE_PIN, GPIO.OUT)

def forward():
    """
    Drives the motor forward by setting the forward channel HIGH
    and the reverse channel LOW.
    """
    GPIO.output(REVERSE_PIN, GPIO.LOW)
    GPIO.output(FORWARD_PIN, GPIO.HIGH)
    print("Motor running forward.")

def reverse():
    """
    Drives the motor in reverse by setting the reverse channel HIGH
    and the forward channel LOW.
    """
    GPIO.output(FORWARD_PIN, GPIO.LOW)
    GPIO.output(REVERSE_PIN, GPIO.HIGH)
    print("Motor running in reverse.")

def stop():
    """
    Stops the motor by setting both channels LOW.
    """
    GPIO.output(FORWARD_PIN, GPIO.LOW)
    GPIO.output(REVERSE_PIN, GPIO.LOW)
    print("Motor stopped.")

# --- Example Usage ---

try:
    print("Running motor forward for 2 seconds...")
    forward()
    time.sleep(5)
    
    print("Stopping motor...")
    stop()
    time.sleep(5)
    
    print("Running motor reverse for 2 seconds...")
    reverse()
    time.sleep(5)
    
    print("Stopping motor...")
    stop()
    time.sleep(5)
    
except KeyboardInterrupt:
    print("Interrupted by user.")

# Cleanup GPIO on exit
GPIO.cleanup()
