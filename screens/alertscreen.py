import webcolors

wc = webcolors.name_to_rgb
import config
import toucharea
import pygame
from config import debugPrint
import screen
import utilities
import eventlist


class AlertsScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "Build Alerts Screen")

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor', 'KeyCharColorOn', 'KeyCharColorOff',
								 CharSize=[20], Font='droidsansmono',
								 Message=[], DeferTime="2 minutes", ActKeyLabel='Fix It')

		self.Defer = utilities.get_timedelta(self.DeferTime)
		self.NodeWatch = []
		self.Keys = {}

		self.Keys['defer'] = toucharea.ManualKeyDesc('defer', ['Defer'], self.KeyColor, self.KeyCharColorOn,
													 self.KeyCharColorOff,
													 center=(config.screenwidth/2, config.screenheight/2 + 30),
													 size=(config.screenwidth, 30), proc=self.DeferAction)

		self.Keys['clearcond'] = toucharea.ManualKeyDesc('clearcond', self.ActKeyLabel, self.KeyColor,
														 self.KeyCharColorOn, self.KeyCharColorOff,
														 center=(config.screenwidth/2, config.screenheight/2 - 30),
														 size=(config.screenwidth, 30), proc=self.ClearCondition)
		for i in range(len(self.CharSize), len(self.Message)):
			self.CharSize.append(self.CharSize[-1])
		self.Alert = None
		config.alertscreens[screenname] = self
		self.DimTO = 0
		self.PersistTO = 0
		utilities.register_example("AlertsScreen", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     ClockScreenDesc:" + str(self.CharColor) + ":" + str(
			self.OutFormat) + ":" + str(self.CharSize)

	def DeferAction(self, presstype):
		debugPrint('Screen', 'Alertscreen manual defer: ' + self.name)
		E = eventlist.AlertEventItem(id(self), 'self deferred screen: ' + self.name, self.Alert)
		config.DS.Tasks.AddTask(E, self.Defer)
		self.Alert.state = 'Deferred'
		config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Manual defer an alert')

	# config.DS.SwitchScreenOld(config.HomeScreen)

	def EnterScreen(self):
		pass

	def ClearCondition(self, presstype):
		print 'ACTION KEY'

	def InitDisplay(self, nav):
		super(AlertsScreenDesc, self).InitDisplay(nav)

		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		l = []

		for i, ln in enumerate(self.Message):
			l.append(
				config.fonts.Font(self.CharSize[i], self.Font).render(ln, 0, wc(self.KeyCharColorOn)))
			h = h + l[i].get_height()
		s = (usefulheight - h)/(len(l) - 1)

		config.screen.fill(wc(self.BackgroundColor),
						   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
		vert_off = config.topborder
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width())/2
			config.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		self.PaintKeys()
		pygame.display.update()

	def ExitScreen(self):
		debugPrint('Screen', 'Alert screen defer to another screen: ' + self.name)
		E = eventlist.AlertEventItem(id(self), 'external deferred screen: ' + self.name, self.Alert)
		config.DS.Tasks.AddTask(E, self.Defer)
		pass


config.alertscreentype = AlertsScreenDesc
config.screentypes["Alert"] = AlertsScreenDesc
