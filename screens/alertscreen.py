import pygame
import traceback

import alerttasks
import debug
import fonts
import hw
import keyspecs
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from logsupport import ConsoleDetail
from utilfuncs import wc

alertscreens = {}


class AlertsScreenDesc(screen.ScreenDesc):
	global alertscreens

	def __init__(self, screensection, screenname):
		global alertscreens
		screen.ScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "Build Alerts Screen")
		self.NavKeysShowing = False
		screen.IncorporateParams(self, screenname, {'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff'}, screensection)
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=fonts.monofont, MessageBack='',
									Message=[], DeferTime="2 minutes", BlinkTime=0)
		if self.MessageBack == '':
			self.MessageBack = self.BackgroundColor
		self.DimTO = 0  # alert screens don't dim or yield voluntarily
		self.PersistTO = 0
		self.BlinkTimer = None
		self.TimerName = 0
		self.DeferTimer = None

		self.Msg = True

		messageareapart = .7
		messageareaheight = (
									hw.screenheight - 2 * screens.topborder) * messageareapart  # no Nav keys todo switch to new screen sizing
		alertbutheight = (hw.screenheight - messageareaheight - 2 * screens.topborder) / 2
		self.upperleft = (screens.horizborder, screens.topborder)

		self.Defer = utilities.get_timedelta(self.DeferTime)

		self.Keys = {'defer': toucharea.ManualKeyDesc(self, 'defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													  self.KeyCharColorOff,
													  center=(hw.screenwidth / 2,
															  screens.topborder + messageareaheight + 0.5 * alertbutheight),
													  size=(
														  hw.screenwidth - 2 * screens.horizborder, alertbutheight),
													  proc=self.DeferAction)}

		if 'Action' in screensection:
			action = screensection['Action']
			self.Keys['action'] = keyspecs.CreateKey(self, action, '*Action*')
			# this is only case so far that is a user descibed key that gets explicit positioning so just do it here
			self.Keys['action'].Center = (
				hw.screenwidth / 2, screens.topborder + messageareaheight + 1.5 * alertbutheight)
			self.Keys['action'].Size = (hw.screenwidth - 2 * screens.horizborder, alertbutheight)
			self.Keys['action'].State = True  # for appearance only
			self.Keys['action'].FinishKey((0, 0), (0, 0))
		else:
			pass
		# no key created - just a blank spot on the alert screen

		#

		for i in range(len(self.CharSize), len(self.Message)):
			self.CharSize.append(self.CharSize[-1])

		h = 0
		l = []

		for i, ln in enumerate(self.Message):
			l.append(
				fonts.fonts.Font(self.CharSize[i], self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (messageareaheight - h) / (len(l))

		self.messageimage = pygame.Surface((hw.screenwidth - 2 * screens.horizborder, messageareaheight))
		self.messageblank = pygame.Surface((hw.screenwidth - 2 * screens.horizborder, messageareaheight))
		self.messageimage.fill(wc(self.MessageBack))
		self.messageblank.fill(wc(self.BackgroundColor))

		vert_off = s / 2
		for i in range(len(l)):
			horiz_off = (hw.screenwidth - l[i].get_width()) / 2 - screens.horizborder
			self.messageimage.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()

		self.Alert = None  # gets filled in by code that parses/defines an alert that invokes the screen
		alertscreens[screenname] = self
		self.DimTO = 0
		self.PersistTO = 0
		utilities.register_example("AlertsScreen", self)

	# noinspection PyUnusedLocal
	def DeferAction(self):
		debug.debugPrint('Screen', 'Alertscreen manual defer: ' + self.name)
		self.Alert.state = 'Deferred'
		# Deferral timer will get set in Exit Screen
		screens.DS.SwitchScreen(screens.HomeScreen, 'Bright', 'Manual defer an alert', newstate='Home')

	# noinspection PyUnusedLocal
	def BlinkMsg(self, param):
		if not self.Active:
			# race condition posted a blink just as screen was exiting so skip screen update
			return
		if self.Msg:
			hw.screen.blit(self.messageimage, self.upperleft)
		else:
			hw.screen.blit(self.messageblank, self.upperleft)
		pygame.display.update()
		self.Msg = not self.Msg

	def InitDisplay(self, nav):
		super(AlertsScreenDesc, self).InitDisplay(nav)

		self.PaintBase()
		self.PaintKeys()
		pygame.display.update()
		self.Msg = True
		if self.BlinkTime != 0:
			self.TimerName += 1
			self.BlinkTimer = timers.RepeatingPost(float(self.BlinkTime),
												   name=self.name + '-Blink-' + str(self.TimerName), proc=self.BlinkMsg,
												   start=True)
		else:
			hw.screen.blit(self.messageimage, self.upperleft)
			pygame.display.update()

	def NodeEvent(self, hub='', node=0, value=0, varinfo=()):
		logsupport.Logs.Log("ISY event to alert screen: ", self.name + ' ' + str(node) + ' ' + str(value),
							severity=ConsoleDetail)

	def ExitScreen(self):
		if self.BlinkTimer is not None:
			self.BlinkTimer.cancel()

		if self.Alert.trigger.IsTrue():  # if the trigger condition is still true requeue post deferral
			self.Alert.state = 'Deferred'
			self.TimerName += 1
			self.DeferTimer = timers.OnceTimer(self.Defer, start=True, name=self.name + '-Defer-' + str(self.TimerName),
											   proc=alerttasks.HandleDeferredAlert, param=self.Alert)
			debug.debugPrint('Screen', 'Alert screen defer to another screen: ' + self.name)
			logsupport.Logs.Log("Alert screen " + self.name + " deferring", severity=ConsoleDetail)
		else:
			debug.debugPrint('Screen', 'Alert screen cause cleared: ' + self.name)
			logsupport.Logs.Log("Alert screen " + self.name + " cause cleared", severity=ConsoleDetail)


screens.screentypes["Alert"] = AlertsScreenDesc
