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

	try:
		# if this system has the newer screen control then turn off the SMTPE control so PWM works
		with open('/sys/class/backlight/soc:backlight/brightness', 'w') as f:
			f.write('0')
	except:
		pass


	wiringpi.wiringPiSetupGpio()
	wiringpi.pinMode(18, 2)
	wiringpi.pwmSetMode(wiringpi.PWM_MODE_MS)  # default balanced mode makes screen dark at about 853/1024
	wiringpi.pwmWrite(18, 1024)


def GoDim(level):
	wiringpi.pwmWrite(18, (level*1024)/100)


def GoBright(level):
	wiringpi.pwmWrite(18, (level*1024)/100)
