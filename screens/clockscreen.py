import webcolors

wc = webcolors.name_to_rgb
import config
import time
import pygame
from config import debugPrint
import screen
import utilities
from eventlist import ProcEventItem


class ClockScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "Build Clock Screen")
		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', CharSize=[20], Font='droidsansmono', OutFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.KeyList = None  # no touch areas active on this screen
		self.NodeWatch = []  # no ISY node changes are of interest to this screen
		utilities.register_example("ClockScreen", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     ClockScreenDesc:" + str(self.CharColor) + ":" + str(
			self.OutFormat) + ":" + str(self.CharSize)

	def repaintClock(self):
		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		l = []

		for i in range(len(self.OutFormat)):
			l.append(
				config.fonts.Font(self.CharSize[i], self.Font).render(time.strftime(self.OutFormat[i]),
																	  0, wc(
						self.CharColor)))
			h = h + l[i].get_height()
		s = (usefulheight - h)/(len(l) - 1)

		config.screen.fill(wc(self.BackgroundColor),
						   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
		vert_off = config.topborder
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width())/2
			config.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		pygame.display.update()
		I = ProcEventItem(id(self), 'repaint', 1, self.repaintClock)
		config.DS.Tasks.AddTask(I)

	def EnterScreen(self):
		self.NodeWatch = []

	def InitDisplay(self, nav):
		super(ClockScreenDesc, self).InitDisplay(nav)
		self.repaintClock()

config.screentypes["Clock"] = ClockScreenDesc
