import subprocess
from collections import OrderedDict

import pygame
import webcolors

import config
import toucharea
from config import debugprint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITEXIT
from utilities import interval_str

wc = webcolors.name_to_rgb
from logsupport import ConsoleError
import time
import sys
import utilities
import screen

fixedoverrides = {'CharColor': 'white', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'], 'DimTO': 100000}


def SetUpMaintScreens():
	Exits = MaintScreenDesc(
		OrderedDict([('shut', ('Shutdown Console', doexit)), ('restart', ('Restart Console', doexit)),
					 ('shutpi', (('Shutdown Pi'), doexit)), ('reboot', (('Reboot Pi'), doexit)),
					 ('return', ('Return', None))]))
	Beta = MaintScreenDesc(
		OrderedDict([('stable', (('Use Stable Release'), dobeta)), ('beta', (('Use Beta Release'), dobeta)),
					 ('fetch', (('Download Beta'), dobeta))]))
	LogDisp = LogDisplayScreen()
	config.MaintScreen = MaintScreenDesc(
		OrderedDict([('return', ('Exit Maintenance', None)), ('log', ('Show Log', LogDisp.showlog)),
					 ('beta', ('Select Version', Beta.HandleScreen)), ('exit', ('Exit/Restart', Exits.HandleScreen))]))
	for screen in config.screentypes:
		pass



def doexit(K):
	if K.name == 'shut':
		Exit_Options("Manual Shutdown Requested", "Shutting Down")
	#		sys.exit()
	elif K.name == 'restart':
		Exit_Options("Console Restart Requested", "Restarting")
	#		z = 'nohup /bin/bash -c \" echo c1 > /home/pi/c1 && sleep 3 && echo c2 > /home/pi/c2 && python -u ' + \
	#			sys.argv[0] + ' ' + config.configfile + '\"'
	#		print z
	#		subprocess.Popen(z, shell=True)
	#		sys.exit()
	elif K.name == 'shutpi':
		Exit_Options("Shutdown Pi Requested", "Shutting Down Pi")
	#		subprocess.Popen('sudo shutdown -P now', shell=True)
	#		sys.exit()
	elif K.name == 'reboot':
		Exit_Options("Reboot Pi Requested", "Rebooting Pi")
	#		subprocess.Popen('sudo reboot', shell=True)
	#		sys.exit()

	subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + K.name + ' ' + config.configfile, shell=True)
	sys.exit()


def errorexit(opt):
	if opt == 'restart':
		Exit_Options('Error restart', 'Error - Restarting')
	elif opt == 'reboot':
		Exit_Options('Error reboot', 'Error - Rebooting Pi')

	subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + opt + ' ' + config.configfile, shell=True)
	sys.exit()

def dobeta(K):
	if K.name == 'stable':
		subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)
	elif K.name == 'beta':
		subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)
	elif K.name == 'fetch':
		subprocess.Popen('sudo /bin/bash -e scripts/getcurrentbeta', shell=True)

def Exit_Options(msg, scrnmsg):
	config.screen.fill(wc("red"))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
	config.Logs.Log(msg)
	pygame.display.update()
	time.sleep(2)


def gotoscreen(K):
	pass


class LogDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		screen.BaseKeyScreenDesc.__init__(self, None, 'LOG', withnav=False)
		self.keysbyord = [toucharea.TouchPoint((config.screenwidth/2, config.screenheight/2),
											   (config.screenwidth, config.screenheight))]
		utilities.register_example("LogDisplayScreen", self)

	def showlog(self, K):
		item = 0
		while item >= 0:
			item = config.Logs.RenderLog(self.BackgroundColor, start=item)
			temp = config.DS.NewWaitPress(self)


class MaintScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, keys):
		debugprint(config.dbgscreenbuild, "Build Maintenance Screen")
		screen.BaseKeyScreenDesc.__init__(self, fixedoverrides, 'Maint', withnav=False)
		utilities.LocalizeParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.keysbyord = []
		for k, kt in keys.iteritems():
			self.keysbyord.append(
				toucharea.ManualKeyDesc(k, [kt[0]], 'gold', 'black', 'black', KOn='black', KOff='black', proc=kt[1]))
		topoff = self.TitleFontSize + self.SubFontSize
		self.LayoutKeys(topoff, config.screenheight - 2*config.topborder - topoff)
		utilities.register_example("MaintScreenDesc", self)

	def ShowScreen(self):
		self.PaintBase()
		r = config.fonts.Font(self.TitleFontSize, '', True, True).render("Console Maintenance", 0, wc(self.CharColor))
		rl = (config.screenwidth - r.get_width())/2
		config.screen.blit(r, (rl, config.topborder))
		r = config.fonts.Font(self.SubFontSize, '', True, True).render(
			"Up: " + interval_str(time.time() - config.starttime),
			0, wc(self.CharColor))
		rl = (config.screenwidth - r.get_width())/2
		config.screen.blit(r, (rl, config.topborder + self.TitleFontSize))
		self.PaintKeys()
		pygame.display.update()

	def HandleScreen(self, newscr=True):
		config.toDaemon.put([])
		# stop any watching for device stream
		Logs = config.Logs
		Logs.Log("Entering Maint Screen")

		while 1:
			self.ShowScreen()
			choice = config.DS.NewWaitPress(self)
			if choice[0] in (WAITNORMALBUTTON, WAITNORMALBUTTONFAST):
				K = self.keysbyord[choice[1]]
				if callable(K.RealObj):
					K.RealObj(K)
					return config.MaintScreen
				elif K.RealObj == None:
					return config.HomeScreen
				else:
					pass  # todo error?  what if multitap or 5 tap here
					Logs.Log("Internal Error", severity=ConsoleError)
			elif choice[0] == WAITEXIT:
				return None
			else:
				Logs.Log("Internal Error Maint from Press", choice[0], severity=ConsoleError)
				return choice[1]  # todo what is this
