import os
import platform
import socket

import pygame
import wiringpi

disklogging = True

IsDim = False
DimType = 'None'

screen = None  # pygame screen to blit on etc

baseheight = 480  # program design height
basewidth = 320  # program design width
dispratioW = 1
dispratioH = 1
screenwidth = 0
screenheight = 0
dimpin = 0

bootime = 0
osversion = ""
hwinfo = ""

hostname = socket.gethostname()
screentype = ""
portrait = True


def scaleW(p):
	return int(round(float(p) * float(dispratioW)))


def scaleH(p):
	return int(round(float(p) * float(dispratioH)))



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
def initOS(scrntyp, configdir):
	global bootime, osversion, hwinfo, screentype, hostname, screenwidth, screenheight, portrait, dispratioW, dispratioH, DimType, dimpin

	screentype = scrntyp

	os.nice(-10)

	# hostname = socket.gethostname()
	# get platform info
	with open('/proc/stat', 'r') as f:
		for line in f:
			if line.startswith('btime'):
				bootime = int(line.split()[1])
	osversion = platform.platform()
	with open('/proc/device-tree/model') as f:
		hwinfo = f.read()

	screendefs = {}
	with open('screendefinitions') as f:
		defs = f.read().splitlines()
		for l in defs:
			screenitem = l.split('|')
			screendefs[screenitem[0]] = screenitem[1:]
	try:
		# allow overwrite of system values
		with open(configdir + '/screendefinitions') as f:
			defs = f.read().splitlines()
			for l in defs:
				screenitem = l.split('|')
				screendefs[screenitem[0]] = screenitem[1:]
	except:
		pass

	if screentype not in screendefs:
		print('Screen type undefined')
		raise ValueError

	if screendefs[screentype][1] != 'XWin':
		if 'DISPLAY' in os.environ: del os.environ['DISPLAY']
	os.environ['SDL_FBDEV'] = screendefs[screentype][0]
	os.environ['SDL_VIDEODRIVER'] = screendefs[screentype][1]
	DimType = screendefs[screentype][2]

	if DimType in ('PWM18', 'PWM19'):
		if DimType == 'PWM18':
			dimpin = 18
		elif DimType == 'PWM19':
			dimpin = 19
		try:
			# if this system has the newer screen control then turn off the SMTPE control so PWM works
			with open('/sys/class/backlight/soc:backlight/brightness', 'w') as f:
				f.write('0')
		except:
			pass

		wiringpi.wiringPiSetupGpio()
		wiringpi.pinMode(dimpin, 2)
		wiringpi.pwmSetMode(wiringpi.PWM_MODE_MS)  # default balanced mode makes screen dark at about 853/1024
		wiringpi.pwmWrite(dimpin, 1024)

	# print('Screen: {}  Device: {} Driver: {} Dim: {}'.format(screentype, os.environ['SDL_FBDEV'],
	#														 os.environ['SDL_VIDEODRIVER'], DimType))

	pygame.display.init()
	screenwidth, screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)

	if screenwidth > screenheight:
		portrait = False

	dispratioW = float(screenwidth) / float(basewidth)
	dispratioH = float(screenheight) / float(baseheight)

	GoBright(100)


def GoDimPWM(level):
	# This version of hw uses the real hw pwm for screen dimming - much better appearance
	wiringpi.pwmWrite(dimpin, int((level * 1024) // 100))


def GoDimPi7(level):
	with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/brightness', 'w') as f:
		f.write(str(level * 255 // 100))


def GoDimOnOff(level):
	with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/bl_power', 'w') as f:
		if level == 0:
			f.write('1')
		else:
			f.write('0')


dimmethods = {'Pi7': GoDimPi7,
			  'PWM': GoDimPWM,
			  'OnOff': GoDimOnOff}


def GoDim(level):
	global IsDim, DimType
	IsDim = True
	if DimType in dimmethods:
		dimmethods[DimType](level)
	else:
		pass


def GoBright(level):
	global IsDim, DimType
	IsDim = False
	if DimType in dimmethods:
		dimmethods[DimType](level)
	else:
		pass
