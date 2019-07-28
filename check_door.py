#!/usr/bin/python

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

top = GPIO.input(10)
bottom = GPIO.input(11)

if top == GPIO.HIGH:
    if bottom == GPIO.LOW:
        print("Door is OPEN")
    else:
        print("ERROR: Door cannot be both open and closed?")
else:
    if bottom == GPIO.HIGH:
        print("Door is CLOSED")
    else:
        print("Door is neither OPEN nor CLOSED")
