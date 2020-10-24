ScreenType = 'Alert'

import pygame

import alerttasks
import debug
import displayupdate
import fonts
import hw
import keyspecs
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from logsupport import ConsoleDetail, ConsoleWarning
from utilfuncs import wc

alertscreens = {}


class AlertsScreenDesc(screen.ScreenDesc):
	global alertscreens

	# todo add centermes option, make clocked and use clock for blinking, move to content repaint, allow messages with store refs

	def __init__(self, screensection, screenname, Clocked=0):
		global alertscreens
		super().__init__(screensection, screenname, Clocked=1, Type=ScreenType)
		debug.debugPrint('Screen', "Build Alerts Screen")
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		screen.IncorporateParams(self, screenname, {'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff'}, screensection)
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=fonts.monofont, MessageBack='',
									Message=[], CenterMessage=True, DeferTime="2 minutes", BlinkTime=0)
		if self.MessageBack == '':
			self.MessageBack = self.BackgroundColor
		self.DimTO = 0  # alert screens don't dim or yield voluntarily
		self.PersistTO = 0
		self.TimerName = 0
		self.DeferTimer = None

		self.Msg = True

		messageareapart = .7
		self.messageareaheight = (
										 hw.screenheight - 2 * self.TopBorder) * messageareapart  # no Nav keys todo switch to new screen sizing
		alertbutheight = (hw.screenheight - self.messageareaheight - 2 * self.TopBorder) / 2
		self.upperleft = (self.HorizBorder, self.TopBorder)

		self.Defer = utilities.get_timedelta(self.DeferTime)

		self.Keys = {'defer': toucharea.ManualKeyDesc(self, 'defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													  self.KeyCharColorOff,
													  center=(hw.screenwidth / 2,
															  self.TopBorder + self.messageareaheight + 0.5 * alertbutheight),
													  size=(
														  hw.screenwidth - 2 * self.HorizBorder, alertbutheight),
													  proc=self.DeferAction)}

		if 'Action' in screensection:
			action = screensection['Action']
			self.Keys['action'] = keyspecs.CreateKey(self, action, '*Action*')
			# this is only case so far that is a user descibed key that gets explicit positioning so just do it here
			self.Keys['action'].Center = (
				hw.screenwidth / 2, self.TopBorder + self.messageareaheight + 1.5 * alertbutheight)
			self.Keys['action'].Size = (hw.screenwidth - 2 * self.HorizBorder, alertbutheight)
			self.Keys['action'].State = True  # for appearance only
			self.Keys['action'].FinishKey((0, 0), (0, 0))
		else:
			pass
		# no key created - just a blank spot on the alert screen

		#

		for i in range(len(self.CharSize), len(self.Message)):
			self.CharSize.append(self.CharSize[-1])

		self.messageblank = pygame.Surface((hw.screenwidth - 2 * self.HorizBorder, self.messageareaheight))
		self.messageblank.fill(wc(self.BackgroundColor))

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

	def InitDisplay(self, nav):  # todo fix for specific repaint
		self.BlinkState = True
		if self.BlinkTime != 0:
			self.NextBlink = self.BlinkTime
		print('init {} {}'.format(self.BlinkState, self.NextBlink))
		super().InitDisplay(nav)

	def ReInitDisplay(self):
		if self.BlinkTime != 0:
			self.NextBlink -= 1
			if self.NextBlink <= 0:
				self.BlinkState = not self.BlinkState
				self.NextBlink = self.BlinkTime
		print('reinit {} {}'.format(self.BlinkState, self.NextBlink))
		super().ReInitDisplay()

	def ScreenContentRepaint(self):
		h = 0
		l = []

		# todo process dynamics for message

		for i, ln in enumerate(self.Message):
			l.append(
				fonts.fonts.Font(self.CharSize[i], self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (self.messageareaheight - h) / (len(l))

		self.messageimage = pygame.Surface((hw.screenwidth - 2 * self.HorizBorder, self.messageareaheight))
		self.messageimage.fill(wc(self.MessageBack))

		vert_off = s / 2
		for i in range(len(l)):
			horiz_off = (hw.screenwidth - l[i].get_width()) / 2 - self.HorizBorder
			self.messageimage.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		if self.BlinkState:
			hw.screen.blit(self.messageimage, self.upperleft)
		else:
			hw.screen.blit(self.messageblank, self.upperleft)

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)

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


screens.screentypes[ScreenType] = AlertsScreenDesc
