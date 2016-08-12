import os

import wiringpi

import config

disklogging = True
touchdevice = True


# This version of hw uses the real hw pwm for screen dimming - much better appearance

def initOS():
	os.environ['SDL_FBDEV'] = '/dev/fb1'
	os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
	os.environ['SDL_MOUSEDRV'] = 'TSLIB'
	os.environ['SDL_VIDEODRIVER'] = 'fbcon'

	wiringpi.wiringPiSetupGpio()
	wiringpi.pinMode(18, 2)
	wiringpi.pwmSetMode(wiringpi.PWM_MODE_MS)  # default balanced mode makes screen dark at about 853/1024
	wiringpi.pwmWrite(18, 1024)


def GoDim():
	wiringpi.pwmWrite(18, (config.DimLevel*1024)/100)


def GoBright():
	wiringpi.pwmWrite(18, (config.BrightLevel*1024)/100)
