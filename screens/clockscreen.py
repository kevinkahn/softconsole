import webcolors

wc = webcolors.name_to_rgb
import config
import time
import pygame
from config import debugprint, WAITEXIT
import screen
import utilities
from utilities import scaleH


class ClockScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugprint(config.dbgscreenbuild, "Build Clock Screen")
		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, CharSize=[20], Font='droidsansmono', OutFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		utilities.register_example("ClockScreen", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     ClockScreenDesc:" + str(self.CharColor) + ":" + str(
			self.OutFormat) + ":" + str(self.CharSize)

	def HandleScreen(self, newscr=True):

		# stop any watching for device stream
		config.toDaemon.put([])

		# config.screen.fill(wc(self.BackgroundColor))
		self.PaintBase()

		def repaintClock(cycle):
			# param ignored for clock
			usefulheight = config.screenheight - config.topborder - config.botborder
			h = 0
			l = []

			for i in range(len(self.OutFormat)):
				l.append(
					config.fonts.Font(int(scaleH(self.CharSize[i])), self.Font).render(time.strftime(self.OutFormat[i]),
																					   0, wc(
							self.CharColor)))  # todo pixel - as a spec'd screen should it scale?
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

		repaintClock(0)
		# config.DS.draw_cmd_buttons(config.screen, self)

		while 1:
			choice = config.DS.NewWaitPress(self, callbackproc=repaintClock, callbackint=1)
			if choice[0] == WAITEXIT:
				return choice[1]


config.screentypes["Clock"] = ClockScreenDesc
