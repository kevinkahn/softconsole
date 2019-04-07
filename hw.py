import os
import platform
import socket

import pygame
import wiringpi

disklogging = True
touchdevice = True
IsDim = False
PWMDim = True

baseheight = 480  # program design height
basewidth = 320  # program design width
dispratioW = 1
dispratioH = 1
screenwidth = 0
screenheight = 0

bootime = 0
osversion = ""
hwinfo = ""

hostname = ""
screentype = ""
portrait = True


def scaleW(p):
	return int(round(float(p) * float(dispratioW)))


def scaleH(p):
	return int(round(float(p) * float(dispratioH)))


# This version of hw uses the real hw pwm for screen dimming - much better appearance

def GoDim(level):
	global IsDim, PWMDim
	IsDim = True
	if PWMDim:
		GoDimPWM(level)
	else:
		GoDimPi7(level)


def GoBright(level):
	global IsDim, PWMDim
	IsDim = False
	if PWMDim:
		GoDimPWM(level)
	else:
		GoDimPi7(level)


# noinspection PyUnusedLocal
def ResetScreenLevel(storeitem, old, val, dim, unusedsrc):
	global IsDim
	if IsDim and dim:
		# screen is dim - reset its level
		GoDim(val)
	elif not IsDim and not dim:
		# screen is bright and bright level reset - reset its level
		GoDim(val)


# noinspection PyBroadException
def initOS(scrntyp):
	global PWMDim, bootime, osversion, hwinfo, screentype, hostname, screenwidth, screenheight, portrait, dispratioW, dispratioH

	screentype = scrntyp

	os.nice(-10)

	hostname = socket.gethostname()
	# get platform info
	with open('/proc/stat', 'r') as f:
		for line in f:
			if line.startswith('btime'):
				bootime = int(line.split()[1])
	osversion = platform.platform()
	with open('/proc/device-tree/model') as f:
		hwinfo = f.read()

	if screentype == 'pi7':
		os.environ['SDL_FBDEV'] = '/dev/fb0'
		os.environ['SDL_NOMOUSE'] = '1'
		os.environ['SDL_MOUSEDEV'] = ''
		os.environ['SDL_MOUSEDRV'] = ''
		os.environ['SDL_VIDEODRIVER'] = 'fbcon'
		PWMDim = False
	elif screentype in ('35r', '28c', '28r'):
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
		PWMDim = True
	else:  # todo delete if 28r works and waveshare works
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
		PWMDim = True

	pygame.display.init()
	screenwidth, screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)
	if screenwidth > screenheight:
		portrait = False

	dispratioW = float(screenwidth) / float(basewidth)
	dispratioH = float(screenheight) / float(baseheight)

	GoBright(100)


def GoDimPWM(level):
	wiringpi.pwmWrite(18, int((level * 1024) // 100))


def GoDimPi7(level):
	with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/brightness', 'w') as f:
		f.write(str(level * 255 // 100))
