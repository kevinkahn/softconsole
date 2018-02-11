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

CreateWeathBlock = weatherinfo.CreateWeathBlock

class TimeTempScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New TimeTempDesc ", screenname)

		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'WunderKey', location='', CharSize=[20],
								 Font=config.monofont,
								 Fcst2Column=False, FcstIcon=True,CondIcon=True,
								 CenterMultiline=False, FcstCenter=False,
								 TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
								 ForecastFormat=[], ForecastDays=1, SkipDays=0)
		if self.ForecastDays + self.SkipDays > 10:
			self.ForecastDays = 10 - self.SkipDays
			config.Logs.Log("Long forecast requested; days reduced to: "+str(self.ForecastDays),severity=ConsoleWarning)
		if self.Fcst2Column and self.FcstCenter:
			self.Fcst2Column = False
			config.Logs.Log("2 Column and Center can't both be true - setting 2 Column False", severity=ConsoleWarning)
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		self.WInfo = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		for i in range(len(self.CharSize), len(self.TimeFormat) + len(self.ConditionFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.ForecastCharSize = self.CharSize[-1]
		self.ClockRepaintEvent = ProcEventItem(id(self), 'repaintTimeTemp', self.repaintClock)
		self.fmt = weatherinfo.WFormatter()

	def InitDisplay(self, nav):
		self.PaintBase()
		super(TimeTempScreenDesc, self).InitDisplay(nav)
		self.repaintClock()

	def repaintClock(self):
		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		renderedtimelabel = []
		renderedforecast  = []
		sizeindex = 0

		for i in range(len(self.TimeFormat)):
			renderedtimelabel.append(config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					time.strftime(self.TimeFormat[i]), 0, wc(self.CharColor)))
			h = h + renderedtimelabel[-1].get_height()
			sizeindex += 1
		renderedtimelabel.append(
			config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
				# "{d}".format(d=self.scrlabel), 0, wc(self.CharColor)
				self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)
			)
		)
		h = h + renderedtimelabel[-1].get_height()

		if self.WInfo.FetchWeather() == -1:
			errmsg1 = config.fonts.Font(self.CharSize[1],self.Font).render('Weather',0,wc(self.CharColor))
			errmsg2 = config.fonts.Font(self.CharSize[1], self.Font).render('unavailable', 0, wc(self.CharColor))
			errmsg3 = config.fonts.Font(self.CharSize[1], self.Font).render('or error', 0, wc(self.CharColor))
			config.screen.fill(wc(self.BackgroundColor),
							   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
			vert_off = config.topborder
			for tmlbl in renderedtimelabel:
				horiz_off = (config.screenwidth - tmlbl.get_width()) / 2
				config.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + 20 + tmlbl.get_height()
			config.screen.blit(errmsg1,((config.screenwidth - errmsg1.get_width())/2,vert_off))
			config.screen.blit(errmsg2, ((config.screenwidth - errmsg2.get_width()) / 2, vert_off + errmsg1.get_height()))
			config.screen.blit(errmsg3,
							   ((config.screenwidth - errmsg3.get_width()) / 2, vert_off + 2*errmsg1.get_height()))
		else:
			cb = CreateWeathBlock(self.ConditionFormat,self.ConditionFields,self.WInfo.ConditionVals,config.fonts.Font(self.CharSize[-2],self.Font),self.CharColor,self.CondIcon,self.CenterMultiline)
			h = h + cb.get_height()

			maxfcstwidth = 0
			forecastlines = 0
			for dy in range(self.ForecastDays):
				fb = CreateWeathBlock(self.ForecastFormat, self.ForecastFields, self.WInfo.ForecastVals[dy + self.SkipDays], config.fonts.Font(self.ForecastCharSize, self.Font), self.CharColor, self.FcstIcon, self.CenterMultiline)
				renderedforecast.append(fb)
				if fb.get_width() > maxfcstwidth: maxfcstwidth = fb.get_width()
				forecastlines += 1
			forecastitemheight = renderedforecast[-1].get_height()

			if self.Fcst2Column:
				h = h + forecastitemheight * (self.ForecastDays + 1) / 2
				forecastlines = (forecastlines + 1) / 2
				usewidth = config.screenwidth / 2
			else:
				h = h + forecastitemheight * self.ForecastDays
				usewidth = config.screenwidth

			s = (usefulheight - h)/(len(renderedtimelabel)+forecastlines) # not counting condition item makes divisor ok

			config.screen.fill(wc(self.BackgroundColor),
							   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
			vert_off = config.topborder
			for tmlbl in renderedtimelabel:
				horiz_off = (config.screenwidth - tmlbl.get_width())/2
				config.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + s + tmlbl.get_height()

			config.screen.blit(cb, ((config.screenwidth - cb.get_width())/2, vert_off))
			vert_off = vert_off + s + cb.get_height()

			startvert = vert_off
			horiz_off = (usewidth - maxfcstwidth) / 2
			for dy,fcst in enumerate(renderedforecast):
				if self.FcstCenter:
					horiz_off = (usewidth - fcst.get_width())/2
				config.screen.blit(fcst, (horiz_off, vert_off))
				vert_off = vert_off + s + fcst.get_height()
				if (dy == (self.ForecastDays+1)/2 - 1) and self.Fcst2Column:
					horiz_off = horiz_off + usewidth
					vert_off = startvert

		pygame.display.update()
		config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)

config.screentypes["TimeTemp"] = TimeTempScreenDesc
