import os
import RPi.GPIO as GPIO

import config

backlight = None
disklogging = True
touchdevice = True


def initOS():
	global backlight
	os.environ['SDL_FBDEV'] = '/dev/fb1'
	os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
	os.environ['SDL_MOUSEDRV'] = 'TSLIB'
	os.environ['SDL_VIDEODRIVER'] = 'fbcon'

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(18, GPIO.OUT)
	backlight = GPIO.PWM(18, 1024)
	backlight.start(100)


def GoDim():
	global backlight
	backlight.ChangeDutyCycle(config.sysStore.DimLevel)


def GoBright():
	global backlight
	backlight.ChangeDutyCycle(config.sysStore.BrightLevel)
