import os
import platform
import socket
import config

from guicore.screencallmanager import pg
# import wiringpi
import RPi.GPIO as GPIO

disklogging = True

IsDim = False
DimType = 'None'
PWMVal = GPIO.PWM

screen = None  # py-game screen to blit on etc
realscreen = None  # used for soft rotate

baseheight = 480  # program design height
basewidth = 320  # program design width
dispratioW = 1
dispratioH = 1
screenwidth = 0
screenheight = 0

dimpin = 0

boottime = 0
osversion = ""
hwinfo = ""

hostname = socket.gethostname()
screentype = ""


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
	global boottime, osversion, hwinfo, screentype, hostname, screenwidth, screenheight, dispratioW, dispratioH, \
		DimType, dimpin, PWMVal

	screentype = scrntyp

	# os.nice(-10) todo

	# hostname = socket.gethostname()
	# get platform info
	with open('/proc/stat', 'r') as f:
		for line in f:
			if line.startswith('btime'):
				boottime = int(line.split()[1])
	osversion = platform.platform()
	with open('/proc/device-tree/model') as f:
		hwinfo = f.read()

	screendefs = {}
	with open(config.sysStore.ExecDir + '/screendefinitions') as f:
		defs = f.read().splitlines()
		for line in defs:
			screenitem = line.split('|')
			screendefs[screenitem[0]] = screenitem[1:]
	try:
		# allow the overwrite of system values
		with open(configdir + '/screendefinitions') as f:
			defs = f.read().splitlines()
			for line in defs:
				screenitem = line.split('|')
				screendefs[screenitem[0]] = screenitem[1:]
	except Exception:
		pass

	if screentype not in screendefs:
		print('Screen type undefined')
		raise ValueError

	if screendefs[screentype][1] != 'XWin':
		if 'DISPLAY' in os.environ:
			del os.environ['DISPLAY']
	screendev = screendefs[screentype][0]
	if screentype[-1] == 'B':  # Buster system
		if screendev[-1] == '0':  # check if there is a fb1 and use that if available
			try:
				open('/dev/fb1')
				screendev = '/dev/fb1'
			except Exception:
				pass
	os.environ['XDG_RUNTIME_DIR'] = '/home/pi/.xdgdir'  # needed for Bookworm, harmless for earlier versions
	os.environ['SDL_FBDEV'] = screendev
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
		except Exception:
			pass
		# wiringpi.wiringPiSetupGpio()
		# wiringpi.pinMode(dimpin, 2)
		# wiringpi.pwmSetMode(wiringpi.PWM_MODE_MS)  # default balanced mode makes screen dark at about 853/1024
		# wiringpi.pwmWrite(dimpin, 1024)

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(dimpin, GPIO.OUT)
		PWMVal = GPIO.PWM(dimpin, 1500000)
		PWMVal.start(100.0)

	pg.display.init()
	screenwidth, screenheight = (pg.display.Info().current_w, pg.display.Info().current_h)
	config.screenwidth = screenwidth
	config.screenheight = screenheight

	dispratioW = float(screenwidth) / float(basewidth)
	dispratioH = float(screenheight) / float(baseheight)

	GoBright(100)


def GoDimPWM(level):
	# This version of hw uses the real hw pwm for screen dimming - much better appearance
	# wiringpi.pwmWrite(dimpin, int((level * 1024) // 100))
	PWMVal.ChangeDutyCycle(level)


def GoDimPi7(level):
	# noinspection PyBroadException
	try:
		with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/brightness', 'w') as f:
			f.write(str(level * 255 // 100))
	except Exception:
		with open('/sys/class/backlight/10-0045/brightness', 'w') as f:
			f.write(str(level * 255 // 100))


def GoDimOnOff(level):
	with open('/sys/devices/platform/rpi_backlight/backlight/rpi_backlight/bl_power', 'w') as f:
		if level == 0:
			f.write('1')
		else:
			f.write('0')


dimmethods = {'Pi7': GoDimPi7,
			  'PWM18': GoDimPWM,
			  'PWM19': GoDimPWM,
			  'OnOff': GoDimOnOff}


def GoDim(level):
	if config.sysStore.DimToOff:
		level = 0
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


def CleanUp():
	try:
		print("Cleaning up GPIO")
		GPIO.cleanup()
	except Exception as e:
		print(f'Extra call to GPIO cleanup {e}')
