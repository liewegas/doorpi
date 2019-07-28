#!/usr/bin/python

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

old10 = None
old11 = None

while True:
    new10 = GPIO.input(10)
    if old10 != new10:
        if new10 == GPIO.HIGH:
            print("10 is now HIGH")
        else:
            print("10 is now LOW")
        old10 = new10

    new11 = GPIO.input(11)
    if old11 != new11:
        if new11 == GPIO.HIGH:
            print("11 is now HIGH")
        else:
            print("11 is now LOW")
        old11 = new11

    time.sleep(.1)

