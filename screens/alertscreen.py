from utilfuncs import wc
import config
import toucharea
import pygame
import debug
import screen
import utilities
from eventlist import ProcEventItem, AlertEventItem
import keyspecs
import logsupport
from logsupport import ConsoleDetail

alertscreens = {}

class AlertsScreenDesc(screen.ScreenDesc):
	global alertscreens
	def __init__(self, screensection, screenname):
		global alertscreens
		screen.ScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "Build Alerts Screen")
		screen.IncorporateParams(self, screenname, {'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff'}, screensection)
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=config.monofont, MessageBack='',
								 Message=[], DeferTime="2 minutes", BlinkTime=0)
		if self.MessageBack == '':
			self.MessageBack = self.BackgroundColor
		self.DimTO = 0  # alert screens don't dim or yield voluntarily
		self.PersistTO = 0

		self.Msg = True

		messageareapart = .7
		messageareaheight = (config.screenheight - 2 * config.topborder) * messageareapart  # no Nav keys
		alertbutheight = (config.screenheight - messageareaheight - 2 * config.topborder) / 2
		self.upperleft = (config.horizborder, config.topborder)

		self.Defer = utilities.get_timedelta(self.DeferTime)

		self.Keys = {'defer': toucharea.ManualKeyDesc(self, 'defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													  self.KeyCharColorOff,
													  center=(config.screenwidth / 2,
															  config.topborder + messageareaheight + 0.5 * alertbutheight),
													  size=(
													  config.screenwidth - 2 * config.horizborder, alertbutheight),
													  proc=self.DeferAction)}

		if 'Action' in screensection:
			action = screensection['Action']
			self.Keys['action'] = keyspecs.CreateKey(self, action, '*Action*')
			# this is only case so far that is a user descibed key that gets explicit positioning so just do it here
			self.Keys['action'].Center = (
				config.screenwidth / 2, config.topborder + messageareaheight + 1.5 * alertbutheight)
			self.Keys['action'].Size = (config.screenwidth - 2 * config.horizborder, alertbutheight)
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
				config.fonts.Font(self.CharSize[i], self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (messageareaheight - h) / (len(l))

		self.messageimage = pygame.Surface((config.screenwidth - 2 * config.horizborder, messageareaheight))
		self.messageblank = pygame.Surface((config.screenwidth - 2 * config.horizborder, messageareaheight))
		self.messageimage.fill(wc(self.MessageBack))
		self.messageblank.fill(wc(self.BackgroundColor))

		self.BlinkEvent = ProcEventItem(id(self), 'msgblink', self.BlinkMsg)

		vert_off = s / 2
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width()) / 2 - config.horizborder
			self.messageimage.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()

		self.Alert = None
		alertscreens[screenname] = self
		self.DimTO = 0
		self.PersistTO = 0
		utilities.register_example("AlertsScreen", self)

	# noinspection PyUnusedLocal
	def DeferAction(self, presstype):
		debug.debugPrint('Screen', 'Alertscreen manual defer: ' + self.name)
		config.DS.Tasks.RemoveAllGrp(id(self))
		self.Alert.state = 'Deferred'
		config.DS.Tasks.AddTask(AlertEventItem(id(self), 'self deferred screen: ' + self.name, self.Alert), self.Defer)
		config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Manual defer an alert')

	def BlinkMsg(self):
		if self.Msg:
			config.screen.blit(self.messageimage, self.upperleft)
		else:
			config.screen.blit(self.messageblank, self.upperleft)
		pygame.display.update()
		self.Msg = not self.Msg
		config.DS.Tasks.AddTask(self.BlinkEvent, self.BlinkTime)

	def InitDisplay(self, nav):
		super(AlertsScreenDesc, self).InitDisplay(nav)

		self.PaintBase()
		self.PaintKeys()
		pygame.display.update()
		self.Msg = True
		if self.BlinkTime != 0:
			config.DS.Tasks.AddTask(self.BlinkEvent, self.BlinkTime)
		else:
			config.screen.blit(self.messageimage, self.upperleft)
			pygame.display.update()

	def NodeEvent(self, hub='', node=0, value=0, varinfo = ()):
		logsupport.Logs.Log("ISY event to alert screen: ", self.name+ ' ' + str(node) + ' ' + str(value), severity=ConsoleDetail)

	def ExitScreen(self):
		config.DS.Tasks.RemoveAllGrp(id(self))
		if self.Alert.trigger.IsTrue():  # if the trigger condition is still true requeue post deferral
			config.DS.Tasks.AddTask(AlertEventItem(id(self), 'external deferred screen: ' + self.name, self.Alert),
									self.Defer)
			debug.debugPrint('Screen', 'Alert screen defer to another screen: ' + self.name)
			logsupport.Logs.Log("Alert screen " + self.name + " deferring", severity=ConsoleDetail)
		else:
			debug.debugPrint('Screen', 'Alert screen cause cleared: ' + self.name)
			logsupport.Logs.Log("Alert screen " + self.name + " cause cleared", severity=ConsoleDetail)


config.screentypes["Alert"] = AlertsScreenDesc
