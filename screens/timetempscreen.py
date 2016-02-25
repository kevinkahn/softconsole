import time

import webcolors

import config
import screen
import utilities
from config import debugprint, WAITEXIT
from utilities import scaleH

wc = webcolors.name_to_rgb
import weatherinfo
import pygame


class TimeTempScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugprint(config.dbgscreenbuild, "New TimeTempDesc ", screenname)

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, WunderKey='', location='', CharSize=[20], Font='droidsansmono',
								 TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
								 ForecastFormat=[], ForecastDays=1)
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		self.WInfo = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		for i in range(len(self.CharSize), len(self.TimeFormat) + len(self.ConditionFormat) + len(self.ForecastFormat)):
			self.CharSize.append(self.CharSize[-1])

	def HandleScreen(self, newscr=True):
		# stop any watching for device stream
		config.toDaemon.put([])

		self.PaintBase()

		def repaintClock(cycle):
			# param ignored for clock
			usefulheight = config.screenheight - config.topborder - config.botborder
			h = 0
			l = []
			sizeindex = 0
			self.WInfo.FetchWeather()

			for i in range(len(self.TimeFormat)):
				l.append(
					config.fonts.Font(int(scaleH(self.CharSize[sizeindex])), self.Font).render(
						time.strftime(self.TimeFormat[i]),
						0, wc(self.CharColor)))
				# todo pixel - as a spec'd screen should it scale?
				h = h + l[i].get_height()
				sizeindex += 1
			for i in range(len(self.ConditionFormat)):
				vals = [self.WInfo.ConditionVals[fld] for fld in self.ConditionFields]
				l.append(
					config.fonts.Font(int(scaleH(self.CharSize[sizeindex])), self.Font).render(
						self.ConditionFormat[i].format(d=vals), 0, wc(self.CharColor)))
				h = h + l[i].get_height()
				sizeindex += 1
			for dy in range(self.ForecastDays):
				for i in range(len(self.ForecastFormat)):
					vals = [self.WInfo.ForecastVals[dy][fld] for fld in self.ForecastFields]
					l.append(
						config.fonts.Font(int(scaleH(self.CharSize[sizeindex + i])), self.Font).render(
							self.ForecastFormat[i].format(d=vals), 0, wc(self.CharColor)))
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

		while 1:
			choice = config.DS.NewWaitPress(self, callbackproc=repaintClock, callbackint=1)
			if choice[0] == WAITEXIT:
				return choice[1]


config.screentypes["TimeTemp"] = TimeTempScreenDesc
