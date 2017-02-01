import time

import config
import screen
import utilities
from debug import debugPrint
from utilities import wc

import weatherinfo
import pygame
from eventlist import ProcEventItem
from logsupport import ConsoleWarning


class TimeTempScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New TimeTempDesc ", screenname)

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'WunderKey', location='', CharSize=[20],
								 Font='droidsansmono',
								 TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
								 ForecastFormat=[], ForecastDays=1, SkipDays=0)
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		self.WInfo = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		for i in range(len(self.CharSize), len(self.TimeFormat) + len(self.ConditionFormat) + len(self.ForecastFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.ClockRepaintEvent = ProcEventItem(id(self), 'repaintTimeTemp', self.repaintClock)
		self.fmt = weatherinfo.WFormatter()

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

		for i in range(len(self.TimeFormat)):
			l.append(
				config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					time.strftime(self.TimeFormat[i]),
					0, wc(self.CharColor)))
			h = h + l[-1].get_height()
			sizeindex += 1
		l.append(
			config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
				# "{d}".format(d=self.scrlabel), 0, wc(self.CharColor)
				self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)
			)
		)
		h = h + l[-1].get_height()
		if self.WInfo.FetchWeather() == -1:
			l.append(config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
				'Weather N/A', 0, wc(self.CharColor)))
			h = h + l[-1].get_height()
		else:
			for i in range(len(self.ConditionFormat)):
				vals = [self.WInfo.ConditionVals[fld] for fld in self.ConditionFields]
				l.append(
					config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
						# self.ConditionFormat[i].format(d=vals), 0, wc(self.CharColor)))
						self.fmt.format(self.ConditionFormat[i], d=vals), 0, wc(self.CharColor)))
				h = h + l[-1].get_height()
				sizeindex += 1
			for dy in range(self.ForecastDays):
				try:
					for i in range(len(self.ForecastFormat)):
						vals = [self.WInfo.ForecastVals[dy + self.SkipDays][fld] for fld in self.ForecastFields]
						l.append(
							config.fonts.Font(self.CharSize[sizeindex + i], self.Font).render(
								self.fmt.format(self.ForecastFormat[i], d=vals), 0, wc(self.CharColor)))
						#self.ForecastFormat[i].format(d=vals), 0, wc(self.CharColor)))
						h = h + l[-1].get_height()
				except:
					config.Logs.Log('TimeTemp Weather Forecast Error', severity=ConsoleWarning)
					l.append(config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
						'Forecast N/A', 0, wc(self.CharColor)))
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
		config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)

config.screentypes["TimeTemp"] = TimeTempScreenDesc
