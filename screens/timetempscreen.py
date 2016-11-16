import time

import webcolors

import config
import screen
import utilities
from config import debugPrint

wc = webcolors.name_to_rgb
import weatherinfo
import pygame
from eventlist import EventItem


class TimeTempScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New TimeTempDesc ", screenname)

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', WunderKey='', location='', CharSize=[20],
								 Font='droidsansmono',
								 TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
								 ForecastFormat=[], ForecastDays=1, SkipDays=0)
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		self.WInfo = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		for i in range(len(self.CharSize), len(self.TimeFormat) + len(self.ConditionFormat) + len(self.ForecastFormat)):
			self.CharSize.append(self.CharSize[-1])

	def EnterScreen(self):
		self.NodeWatch = []

	def InitDisplay(self, nav):
		self.PaintBase()
		super(TimeTempScreenDesc, self).InitDisplay(nav)
		self.repaintClock()

	def repaintClock(self):
		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		l = []
		sizeindex = 0
		if self.WInfo.FetchWeather() == -1:
			return -1  # error
		# todo add error field handling to below code (self.ConditionErr[cond] and self.ForecastErr[dy][cond]

		for i in range(len(self.TimeFormat)):
			l.append(
				config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					time.strftime(self.TimeFormat[i]),
					0, wc(self.CharColor)))
			h = h + l[-1].get_height()
			sizeindex += 1
		l.append(
			config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
				"{d}".format(d=self.scrlabel), 0, wc(self.CharColor)
			)
		)
		h = h + l[-1].get_height()
		for i in range(len(self.ConditionFormat)):
			vals = [self.WInfo.ConditionVals[fld] for fld in self.ConditionFields]
			l.append(
				config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					self.ConditionFormat[i].format(d=vals), 0, wc(self.CharColor)))
			h = h + l[-1].get_height()
			sizeindex += 1
		for dy in range(self.ForecastDays):
			for i in range(len(self.ForecastFormat)):
				vals = [self.WInfo.ForecastVals[dy + self.SkipDays][fld] for fld in self.ForecastFields]
				l.append(
					config.fonts.Font(self.CharSize[sizeindex + i], self.Font).render(
						self.ForecastFormat[i].format(d=vals), 0, wc(self.CharColor)))
				h = h + l[-1].get_height()

		s = (usefulheight - h)/(len(l) - 1)

		config.screen.fill(wc(self.BackgroundColor),
						   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
		vert_off = config.topborder
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width())/2
			config.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		pygame.display.update()
		I = EventItem(self, '666', 'repaintTimeTemp', 1, self.repaintClock)
		config.DS.Tasks.AddTask(I)

config.screentypes["TimeTemp"] = TimeTempScreenDesc
