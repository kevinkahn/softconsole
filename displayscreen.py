import time

import pygame
import webcolors

import config
import hw
import toucharea
from config import debugPrint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITEXIT, WAITISYCHANGE, WAITEXTRACONTROLBUTTON
from logsupport import ConsoleWarning

wc = webcolors.name_to_rgb


class DisplayScreen(object):

	def __init__(self):

		config.debugPrint("Main", "Screensize: ", config.screenwidth, config.screenheight)
		config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
		config.Logs.Log(
			"Scaling ratio: " + "{0:.2f}".format(config.dispratioW) + ':' + "{0:.2f}".format(config.dispratioH))

		# define user events
		self.TIMER = pygame.event.Event(pygame.USEREVENT + 4)
		self.MAXTIMEHIT = pygame.event.Event(pygame.USEREVENT)
		self.INTERVALHIT = pygame.event.Event(pygame.USEREVENT + 1)
		self.GOHOMEHIT = pygame.event.Event(pygame.USEREVENT + 2)
		self.DIMCYCLE = pygame.event.Event(pygame.USEREVENT + 3)
		self.dimscreenindex = 0
		self.isDim = False
		self.presscount = 0
		self.AS = None
		self.BrightenToHome = False
		self.EventSet = []

	# event set entry is type(owner,id,proc)

	class TimerItem(object):
		def __init__(self):
			self.ownerscreen = None
			self.id = 0
			self.callback = None
			self.type = 0  # Quiet or needs screen
			self.interval = 0  # time interval ?  is this here of is it somehow added in the event list?
			self.targettime = 0  # computed time when should occur - use to handle multiple events in timer window

	def GoDim(self, dim):
		if dim:
			hw.GoDim()
			self.isDim = True
			if self.AS == config.HomeScreen:
				self.BrightenToHome = True
				self.dimscreenindex = 0
				pygame.time.set_timer(self.DIMCYCLE.type, config.DimIdleTimes[0])
				return config.DimIdleList[0]
		else:
			hw.GoBright()
			self.isDim = False
			pygame.time.set_timer(self.DIMCYCLE.type, 0)
			if self.BrightenToHome:
				self.BrightenToHome = False
				return config.HomeScreen

	def MainControlLoop(self, InitScreen):
		"""
		Pick a screen, call its enter
		wait for event (press, daemon notification, timer, event queue item)
		respond to the event (Press -> call screen.press(button, type)
		Queued event -. has a proc to call
		command button -> exit screen pick new one?

		"""
		CurrentScreen = InitScreen
		while True:
			CurrentScreen.EnterScreen()

			event = pygame.fastevent.poll()
			if event.type == pygame.NOEVENT:
				time.sleep(.01)
			elif event.type == pygame.MOUSEBUTTONDOWN:
				pass
			elif event.type == self.TIMER.type:
				pass
			# handle timer events from queue
			# grab first event, check eventtime<now+epsilon
			# timer event queue can have screen callbacks on it or alert event
			# unhide - either provide a call back to displayscreen or just return a code + proc to call after prev screen exits (better?)
			# should we treat GOHOME as such an event or keep special
			# - yes: call associated proc (is there any param needed?
			# - no: set next timer event at nexteventtime - now
			elif event.type == self.GOHOMEHIT.type:
				pass
			# Exit current screen
			# Enter home screen
			elif event.type == self.MAXTIMEINT.type:
				pass
			# set screen dim (do we tell the screen it's dim?
			elif event.type == self.DIMCYCLE.type:
				pass
			# go to next dim screen

			pass




	def NewWaitPress(self, ActiveScreen, callbackint=0, callbackproc=None, callbackcount=0):

		self.AS = ActiveScreen
		cycle = 0
		if callbackint <> 0:  # todo needs a better structural fix for posted actions that persist across Waitpress calls
			pygame.time.set_timer(self.INTERVALHIT.type, int(callbackint*1000))
			cycle = callbackcount if callbackcount <> 0 else 100000000  # essentially infinite
		if self.isDim and self.BrightenToHome:
			pygame.time.set_timer(self.GOHOMEHIT.type, 0)  # in final quiet state so cancel gohome until a touch
		else:
			pygame.time.set_timer(self.MAXTIMEHIT.type,
								  self.AS.DimTO*1000)  # if not in final quiet state set dim timer

		while True:
			rtn = (0, 0)

			event = pygame.fastevent.poll()

			if event.type == pygame.NOEVENT:
				time.sleep(.01)
				pass
			elif event.type == pygame.MOUSEBUTTONDOWN:
				pos = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
				# if self.presscount < 10:  # this is debug code for a weird/unreproducible RPi behavior where touch is off
				#	print pos
				#	self.presscount += 1
				tapcount = 1
				pygame.time.delay(config.MultiTapTime)
				while True:
					eventx = pygame.fastevent.poll()
					if eventx.type == pygame.NOEVENT:
						break
					elif eventx.type == pygame.MOUSEBUTTONDOWN:
						tapcount += 1
						pygame.time.delay(config.MultiTapTime)
					else:
						continue
				if tapcount > 2:
					self.GoDim(False)
					rtn = (WAITEXIT, tapcount)
					break
				# on any touch reset return to home screen
				pygame.time.set_timer(self.GOHOMEHIT.type, int(config.HomeScreenTO)*1000)
				# on any touch restart dim timer and reset to bright if dim
				pygame.time.set_timer(self.MAXTIMEHIT.type, self.AS.DimTO*1000)
				dimscr = self.GoDim(False)
				if dimscr is not None:
					rtn = (WAITEXIT, config.HomeScreen)
					break

				for i in range(len(self.AS.keysbyord)):
					K = self.AS.keysbyord[i]
					if K.touched(pos):
						if tapcount == 1:
							rtn = (WAITNORMALBUTTON, i)
						else:
							rtn = (WAITNORMALBUTTONFAST, i)
				if self.AS.PrevScreen is not None:
					if self.AS.PrevScreenKey.touched(pos):
						rtn = (WAITEXIT, self.AS.PrevScreen)
					elif self.AS.NextScreenKey.touched(pos):
						rtn = (WAITEXIT, self.AS.NextScreen)
				for K in self.AS.ExtraCmdKeys:
					if K.touched(pos):
						rtn = (WAITEXTRACONTROLBUTTON, K.name)
				if rtn[0] <> 0:
					break
				continue

			elif event.type == self.MAXTIMEHIT.type:
				dimscr = self.GoDim(True)
				if dimscr is not None:
					rtn = (WAITEXIT, dimscr)
					break
				continue
			elif event.type == self.DIMCYCLE.type:
				self.dimscreenindex = (self.dimscreenindex + 1)%len(config.DimIdleList)
				pygame.time.set_timer(self.DIMCYCLE.type, config.DimIdleTimes[self.dimscreenindex])
				rtn = (WAITEXIT, config.DimIdleList[self.dimscreenindex])
				break
			elif event.type == self.INTERVALHIT.type:
				if (callbackproc is not None) and (cycle > 0):
					callbackproc(cycle)
					cycle -= 1
				continue
			elif event.type == self.GOHOMEHIT.type:
				rtn = (WAITEXIT, config.HomeScreen)
				break
			else:
				pass  # ignore and flush other events

			if (not config.fromDaemon.empty()) and (cycle == 0):  # todo don't process daemon reports while cycling
				debugPrint('Main', "Q size at main loop ", config.fromDaemon.qsize())
				item = config.fromDaemon.get()
				debugPrint('Main', time.time(), "ISY reports change: ", "Key: ", str(item))
				if item[0] == "Log":
					config.Logs.Log(item[1], severity=item[2])
					continue
				elif item[0] == "Node":
					rtn = (WAITISYCHANGE, (item[1], item[2]))
					break
				else:
					config.Logs.Log("Bad msg from watcher: " + str(item), Severity=ConsoleWarning)

				# check for periodic alert items todo



		pygame.time.set_timer(self.INTERVALHIT.type, 0)
		pygame.time.set_timer(self.MAXTIMEHIT.type, 0)

		return rtn
