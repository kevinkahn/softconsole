from keys.keyutils import internalprocs

ScreenType = 'Alert'

import pygame
import functools

from alertsystem import alerttasks
import debug
import fonts
import hw
from keys import keyspecs
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from logsupport import ConsoleDetail
from utilfuncs import wc
from configobj import ConfigObj
from typing import Union
from guicore.switcher import SwitchScreen

alertscreens = {}


class AlertsScreenDesc(screen.ScreenDesc):
	global alertscreens

	def __init__(self, screensection, screenname):
		global alertscreens
		super().__init__(screensection, screenname, Type=ScreenType)
		debug.debugPrint('Screen', "Build Alerts Screen")
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.BlinkState: bool = True
		self.NextBlink: int = 0
		self.BlinkTime: Union[int, list]
		screen.IncorporateParams(self, screenname, {'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff'}, screensection)
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=fonts.monofont, MessageBack='',
									Message=[], CenterMessage=True, DeferTime="2 minutes", BlinkTime=[],
									AutoClear='')
		if self.MessageBack == '':
			self.MessageBack = self.BackgroundColor
		self.DimTO = 0  # alert screens don't dim or yield voluntarily
		self.PersistTO = 0
		self.TimerName = 0
		self.DeferTimer = None
		if not isinstance(self.BlinkTime, list):
			self.BlinkTime = [int(self.BlinkTime), int(self.BlinkTime)]
		else:
			if len(self.BlinkTime) != 2:
				self.BlinkTime = [0, 0]
			else:
				self.BlinkTime = [int(self.BlinkTime[0]), int(self.BlinkTime[1])]

		self.Msg = True

		messageareapart = .7
		self.messageareaheight = (
										 hw.screenheight - 2 * self.TopBorder) * messageareapart  # no Nav keys todo switch to new screen sizing
		alertbutheight = (hw.screenheight - self.messageareaheight - 2 * self.TopBorder) / 2
		self.upperleft = (self.HorizBorder, self.TopBorder)

		self.Defer = utilities.get_timedelta(self.DeferTime)
		self.AutoClearSecs = utilities.get_timedelta(self.AutoClear) if self.AutoClear != '' else None
		self.timetoclear = 0

		self.Keys = {'defer': toucharea.ManualKeyDesc(self, 'defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													  self.KeyCharColorOff,
													  center=(hw.screenwidth / 2,
															  self.TopBorder + self.messageareaheight + 0.5 * alertbutheight),
													  size=(
														  hw.screenwidth - 2 * self.HorizBorder, alertbutheight),
													  proc=self.DeferAction)}

		def CallClear(screentoclear):
			screentoclear.Alert.trigger.ClearTrigger()
			SwitchScreen(screens.HomeScreen, 'Bright', 'Manual defer an alert', newstate='Home')

		if 'Action' in screensection:
			action = screensection['Action']
			self.Keys['action'] = keyspecs.CreateKey(self, action, '*Action*')
		else:
			internalprocs[self.name + '-ACK'] = functools.partial(CallClear, self)
			temp = ConfigObj()
			temp['action'] = {'type': 'PROC', 'ProcName': self.name + '-ACK', 'label': 'Clear'}
			self.Keys['action'] = keyspecs.CreateKey(self, temp['action'], '*Action*')

		# this is only case so far that is a user descibed key that gets explicit positioning so just do it here
		self.Keys['action'].Center = (
			hw.screenwidth / 2, self.TopBorder + self.messageareaheight + 1.5 * alertbutheight)
		self.Keys['action'].Size = (hw.screenwidth - 2 * self.HorizBorder, alertbutheight)
		self.Keys['action'].State = True  # for appearance only
		self.Keys['action'].FinishKey((0, 0), (0, 0))

		self.messageblank = pygame.Surface((hw.screenwidth - 2 * self.HorizBorder, self.messageareaheight))
		self.messageblank.fill(wc(self.BackgroundColor))

		self.Alert = None  # gets filled in by code that parses/defines an alert that invokes the screen
		alertscreens[screenname] = self
		self.DimTO = 0
		self.PersistTO = 0
		utilities.register_example("AlertsScreen", self)

	# noinspection PyUnusedLocal
	def getCharSize(self, lineno):
		return self.CharSize[lineno] if lineno < len(self.CharSize) else self.CharSize[-1]

	def DeferAction(self):
		debug.debugPrint('Screen', 'Alertscreen manual defer: ' + self.name)
		self.Alert.state = 'Deferred'
		# Deferral timer will get set in Exit Screen
		SwitchScreen(screens.HomeScreen, 'Bright', 'Manual defer an alert', newstate='Home')

	def InitDisplay(self, nav):  # todo fix for specific repaint
		self.timetoclear = self.AutoClearSecs
		self.BlinkState = True
		if self.BlinkTime != 0:
			self.NextBlink = self.BlinkTime[not self.BlinkState]
		super().InitDisplay(nav)

	def ReInitDisplay(self):
		if self.timetoclear is not None:
			self.timetoclear -= 1
			if self.timetoclear == 0:
				self.Alert.trigger.ClearTrigger()
				SwitchScreen(screens.HomeScreen, 'Bright', 'Auto cleared alert', newstate='Home')

		if self.BlinkTime != 0:
			self.NextBlink -= 1
			if self.NextBlink <= 0:
				self.BlinkState = not self.BlinkState
				self.NextBlink = self.BlinkTime[not self.BlinkState]
		super().ReInitDisplay()

	def ScreenContentRepaint(self):
		h = 0
		l = []

		# todo process dynamics for message
		Message = utilities.ExpandTextwitVars(self.Message, screenname=self.name)

		for i, ln in enumerate(Message):
			l.append(
				fonts.fonts.Font(self.getCharSize(i), self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (self.messageareaheight - h) / (len(l))

		messageimage = pygame.Surface((hw.screenwidth - 2 * self.HorizBorder, self.messageareaheight))
		messageimage.fill(wc(self.MessageBack))

		vert_off = s / 2
		for i in range(len(l)):
			if self.CenterMessage:
				horiz_off = (hw.screenwidth - l[i].get_width()) / 2 - self.HorizBorder
			else:
				horiz_off = self.HorizBorder
			messageimage.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		if self.BlinkState:
			hw.screen.blit(messageimage, self.upperleft)
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
