import os

import wiringpi

import config

disklogging = True
touchdevice = True
GoDim = None
GoBright = None

# This version of hw uses the real hw pwm for screen dimming - much better appearance


def initOS(screentype):
	global GoDim, GoBright
	if screentype == 'pi7':
		os.environ['SDL_FBDEV'] = '/dev/fb0'
		os.environ['SDL_NOMOUSE'] = '1'
		os.environ['SDL_MOUSEDEV'] = ''
		os.environ['SDL_MOUSEDRV'] = ''
		os.environ['SDL_VIDEODRIVER'] = 'fbcon'
		GoDim = GoDimPi7
		GoBright = GoDimPi7
	elif screentype == '35r':
		os.environ['SDL_FBDEV'] = '/dev/fb1'
		os.environ['SDL_NOMOUSE'] = '1'
		os.environ['SDL_MOUSEDEV'] = ''
		os.environ['SDL_MOUSEDRV'] = ''
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
		GoDim = GoDimPWM
	else:
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
		GoDim = GoDimPWM
		GoBright = GoDimPWM

	GoBright(100)

def GoDimPWM(level):
	wiringpi.pwmWrite(18, (level*1024)/100)

def GoDimPi7(level):
	with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/brightness', 'w') as f:
		f.write(str(level*255/100))



