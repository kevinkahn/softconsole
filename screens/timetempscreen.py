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
								 Font=config.monofont, FcstLayout = 'Block',
								 FcstIcon=True,CondIcon=True,
								 TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
								 ForecastFormat=[], ForecastDays=1, SkipDays=0)
		if self.ForecastDays + self.SkipDays > 10:
			self.ForecastDays = 10 - self.SkipDays
			config.Logs.Log("Long forecast requested; days reduced to: "+str(self.ForecastDays),severity=ConsoleWarning)
		if self.FcstLayout not in ('Block','BlockCentered','LineCentered','2ColVert','2ColHoriz'):
			config.Logs.Log('FcstLayout Param not Block, BlockCentered, LineCentered, 2ColVert, or 2ColHoriz - using "Block" for ' ,
							screenname,severity=ConsoleWarning)
			self.FcstLayout = "Block"
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
		renderedforecast  = []
		sizeindex = 0
		renderedtime = []
		renderedtimelabel = []


		tw = 0
		for i in range(len(self.TimeFormat)):
			renderedtime.append(config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					time.strftime(self.TimeFormat[i]), 0, wc(self.CharColor)))
			h = h + renderedtime[-1].get_height()
			if renderedtime[-1].get_width() > tw: tw = renderedtime[-1].get_width()
			sizeindex += 1
		renderedtimelabel.append(pygame.Surface((tw,h)))
		renderedtimelabel[-1].set_colorkey(wc('black'))
		v = 0
		for l in renderedtime:
			renderedtimelabel[0].blit(l, (((tw - l.get_width())/ 2), v))
			v = v + l.get_height()
		spaces = 1

		if int(self.CharSize[sizeindex]) != 0:
			renderedtimelabel.append(
				config.fonts.Font(self.CharSize[sizeindex], self.Font).render(
					self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)))
			h = h + renderedtimelabel[-1].get_height()
			spaces += 1
		sizeindex += 1

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
			cb = CreateWeathBlock(self.ConditionFormat,self.ConditionFields,self.WInfo.ConditionVals,self.Font,
								  int(self.CharSize[sizeindex]),self.CharColor,self.CondIcon,
								  self.FcstLayout == 'LineCentered')
			h = h + cb.get_height()

			maxfcstwidth = 0
			forecastlines = 0
			spaces += 1
			for dy in range(self.ForecastDays):
				fb = CreateWeathBlock(self.ForecastFormat, self.ForecastFields,
									  self.WInfo.ForecastVals[dy + self.SkipDays], self.Font,
									  [self.ForecastCharSize], self.CharColor, self.FcstIcon,
									  self.FcstLayout == 'LineCentered')
				renderedforecast.append(fb)
				if fb.get_width() > maxfcstwidth: maxfcstwidth = fb.get_width()
				forecastlines += 1
			forecastitemheight = renderedforecast[-1].get_height()

			if self.FcstLayout in ('2ColVert','2ColHoriz'):
				h = h + forecastitemheight * ((self.ForecastDays + 1) / 2)
				forecastlines = (forecastlines + 1) / 2
				usewidth = config.screenwidth / 2
			else:
				h = h + forecastitemheight * self.ForecastDays
				usewidth = config.screenwidth

			s = (usefulheight - h)/(spaces + forecastlines - 1)
			extraspace = (usefulheight - h - s*(spaces + forecastlines - 1))/(spaces)

			config.screen.fill(wc(self.BackgroundColor),
							   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
			vert_off = config.topborder
			#pygame.draw.line(config.screen, wc('white'), (0, vert_off), (400, vert_off))
			for tmlbl in renderedtimelabel:
				horiz_off = (config.screenwidth - tmlbl.get_width())/2
				config.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + s + tmlbl.get_height() + extraspace
				#pygame.draw.line(config.screen, wc('white'), (0, vert_off), (400, vert_off))

			config.screen.blit(cb, ((config.screenwidth - cb.get_width())/2, vert_off))
			vert_off = vert_off + s + cb.get_height() + extraspace
			#pygame.draw.line(config.screen, wc('white'), (0, vert_off), (400, vert_off))

			startvert = vert_off
			maxvert = startvert
			fcstvert = renderedforecast[0].get_height()
			horiz_off = (usewidth - maxfcstwidth) / 2
			for dy,fcst in enumerate(renderedforecast):
				h_off = horiz_off
				v_off = vert_off
				if self.FcstLayout == '2ColHoriz':
					h_off = horiz_off + (dy % 2) * usewidth
					vert_off = vert_off + (dy % 2) * (s + fcstvert)
				elif self.FcstLayout == '2ColVert':
					vert_off = vert_off + s + fcstvert
					if (dy == (self.ForecastDays + 1) / 2 - 1):
						horiz_off = horiz_off + usewidth
						vert_off = startvert
				elif self.FcstLayout in ('BlockCentered', 'LineCentered'):
					vert_off = vert_off + s + fcstvert
					h_off = (usewidth - fcst.get_width())/2
				else:
					vert_off = vert_off + s + fcstvert
				if v_off > maxvert: maxvert = v_off
				config.screen.blit(fcst, (h_off, v_off))

			if self.FcstLayout == '2ColVert': pygame.draw.line(config.screen,wc('white'),(usewidth,startvert+fcstvert/3),(usewidth,maxvert + 2*fcstvert/3))

		#pygame.draw.line(config.screen,wc('white'),(0,vert_off),(400,vert_off))
		#pygame.draw.line(config.screen,wc('black'),(0,config.screenheight-config.botborder),(400,config.screenheight-config.botborder))
		pygame.display.update()
		config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)

config.screentypes["TimeTemp"] = TimeTempScreenDesc
