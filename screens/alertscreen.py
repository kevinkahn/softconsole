from utilities import wc
import config
import toucharea
import pygame
from debug import debugPrint
import screen
import utilities
from eventlist import ProcEventItem, AlertEventItem
import keyspecs


class AlertsScreenDesc(screen.ScreenDesc):
	# noinspection PyDictCreation
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "Build Alerts Screen")

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff',
								 CharSize=[20], Font=config.monofont, MessageBack='',
								 Message=[], DeferTime="2 minutes", BlinkTime=0)

		if self.MessageBack == '':
			self.MessageBack = self.BackgroundColor
		self.DimTO = 0  # alert screens don't dim or yield voluntarily
		self.PersistTO = 0

		self.Msg = True

		messageareapart = .7
		messageareaheight = (config.screenheight - 2*config.topborder)*messageareapart  # no need to allow for Nav keys
		alertbutheight = (config.screenheight - messageareaheight - 2*config.topborder)/2
		self.upperleft = (config.horizborder, config.topborder)


		self.Defer = utilities.get_timedelta(self.DeferTime)
		self.NodeWatch = []
		self.Keys = {}

		self.Keys['defer'] = toucharea.ManualKeyDesc(self, 'defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													 self.KeyCharColorOff,
													 center=(config.screenwidth/2,
															 config.topborder + messageareaheight + 0.5*alertbutheight),
													 size=(config.screenwidth - 2*config.horizborder, alertbutheight),
													 proc=self.DeferAction)
		if 'Action' in screensection:
			action = screensection['Action']
			self.Keys['action'] = keyspecs.CreateKey(self, action, '*Action*')
			# this is only case so far that is a user descibed key that gets explicit positioning so just do it here
			self.Keys['action'].Center = (
			config.screenwidth/2, config.topborder + messageareaheight + 1.5*alertbutheight)
			self.Keys['action'].Size = (config.screenwidth - 2*config.horizborder, alertbutheight)
			self.Keys['action'].State = True  # for appearance only
		else:
			pass
		# no key created - just a blank spot on the alert screen

		for k in self.Keys.itervalues():  # todo relook at Finish Key - can it be done as part of creation?
			k.FinishKey((0, 0), (0, 0))

		for i in range(len(self.CharSize), len(self.Message)):
			self.CharSize.append(self.CharSize[-1])

		h = 0
		l = []

		for i, ln in enumerate(self.Message):
			l.append(
				config.fonts.Font(self.CharSize[i], self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (messageareaheight - h)/(len(l))

		self.messageimage = pygame.Surface((config.screenwidth - 2*config.horizborder, messageareaheight))
		self.messageblank = pygame.Surface((config.screenwidth - 2*config.horizborder, messageareaheight))
		self.messageimage.fill(wc(self.MessageBack))
		self.messageblank.fill(wc(self.BackgroundColor))

		self.BlinkEvent = ProcEventItem(id(self), 'msgblink', self.BlinkMsg)

		vert_off = s/2
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width())/2 - config.horizborder
			self.messageimage.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()


		self.Alert = None
		config.alertscreens[screenname] = self
		self.DimTO = 0
		self.PersistTO = 0
		utilities.register_example("AlertsScreen", self)

	def DeferAction(self, presstype):
		debugPrint('Screen', 'Alertscreen manual defer: ' + self.name)
		config.DS.Tasks.RemoveAllGrp(id(self))
		E = AlertEventItem(id(self), 'self deferred screen: ' + self.name, self.Alert)
		config.DS.Tasks.AddTask(E, self.Defer)
		self.Alert.state = 'Deferred'
		config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Manual defer an alert')

	def BlinkMsg(self):
		if self.Msg:
			config.screen.blit(self.messageimage, self.upperleft)
		else:
			config.screen.blit(self.messageblank, self.upperleft)
		pygame.display.update()
		self.Msg = not self.Msg
		config.DS.Tasks.AddTask(self.BlinkEvent, self.BlinkTime)

	def EnterScreen(self):
		pass

	def InitDisplay(self, nav):
		super(AlertsScreenDesc, self).InitDisplay(nav)

		config.screen.fill(wc(self.BackgroundColor))
		self.PaintKeys()
		pygame.display.update()
		self.Msg = True
		if self.BlinkTime <> 0:
			config.DS.Tasks.AddTask(self.BlinkEvent, self.BlinkTime)

	def ExitScreen(self):
		debugPrint('Screen', 'Alert screen defer to another screen: ' + self.name)
		config.Logs.Log("Alert screen " + self.name + " deferring")
		config.DS.Tasks.RemoveAllGrp(id(self))
		if self.Alert.trigger.IsTrue():  # if the trigger condition is still true requeue post deferral
			E = AlertEventItem(id(self), 'external deferred screen: ' + self.name, self.Alert)
			config.DS.Tasks.AddTask(E, self.Defer)

config.screentypes["Alert"] = AlertsScreenDesc
