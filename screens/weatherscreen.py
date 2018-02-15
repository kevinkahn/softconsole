import pygame
import config
from debug import debugPrint
from utilities import wc
import screen
import logsupport
import weatherinfo
import utilities
import toucharea
from collections import OrderedDict

fsizes = ((20, False, False), (30, True, False), (45, True, True))
"""
num fcst days, 1 or 2 col, format override, spacing, block center, other params from timetemp?
default cols based on screen width > 390 use 2 col
def fcst days based on screen height?
for conditions where to put icon?  Center vertically? with size lesser of % of screen width % of screen height
"""

class WeatherScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		self.fmt = weatherinfo.WFormatter()
		debugPrint('Screen', "New WeatherScreenDesc ", screenname)
		screen.ScreenDesc.__init__(self, screensection, screenname)
		butsize = screen.ButSize(1, 1, 0)
		self.Keys = OrderedDict({'condorfcst': toucharea.TouchPoint('condorfcst', (
		config.horizborder + .5*butsize[0], config.topborder + .5*butsize[1]), butsize,
																	proc=self.CondOrFcst)})
		self.currentconditions = True  # show conditions or forecast

		utilities.LocalizeParams(self, screensection, '-', 'WunderKey', location='')

		self.scrlabel = screen.FlatenScreenLabel(self.label)

		self.errformat = "{d[0]}",'Weather Not Available'
		self.errfields = 'LABEL',

		self.headformat = "{d[0]}", "{d[1]}"
		self.headfields = 'LABEL', 'Location'

		self.footformat = "Readings as of", "{d[0]} ago",
		self.footfields = ('Age',)

		self.condformat = u"{d[0]} {d[1]}\u00B0F",u"  Feels like: {d[2]}\u00B0","Wind {d[3]}"
		self.condfields = ('Sky', 'Temp','Feels','WindStr')

		self.dayformat  = "Sunrise: {d[0]:02d}:{d[1]:02d}","Sunset:  {d[2]:02d}:{d[3]:02d}","Moon rise: {d[4]} set: {d[5]}","{d[6]}% illuminated"
		self.dayfields  = ('SunriseH', 'SunriseM', 'SunsetH', 'SunsetM', 'Moonrise', 'Moonset', 'MoonPct')

		self.fcstformat = u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}","Wind: {d[4]} at {d[5]}"
		self.fcstfields = ('Day', 'High', 'Low', 'Sky','WindDir', 'WindSpd')
		self.forecast = [(1, False, u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}", ('Day', 'High', 'Low', 'Sky')),
						 (1, False, "Wind: {d[0]} at {d[1]}", ('WindDir', 'WindSpd'))]
		self.Info = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		utilities.register_example("WeatherScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     WeatherScreenDesc:" + str(self.CharColor)

	def CondOrFcst(self, press):
		self.currentconditions = not self.currentconditions
		self.ShowScreen(self.currentconditions)

	def ShowScreen(self, conditions):
		self.ReInitDisplay()

		usefulheight = config.screenheight - config.topborder - config.botborder
		vert_off = config.topborder

		if self.Info.FetchWeather() == -1:
			renderedlines = [
				weatherinfo.CreateWeathBlock(self.errformat, self.errfields, self.Info.ConditionVals, "", [45, 30],
											 self.CharColor, False, True, extra={'LABEL': self.scrlabel})]
			for l in renderedlines:
				config.screen.blit(l, ((config.screenwidth - l.get_width()) / 2, vert_off))
				vert_off = vert_off + 30
			config.Logs.Log('Weatherscreen missing weather' + self.name, severity=logsupport.ConsoleWarning)
		else:
			renderedlines = [
				weatherinfo.CreateWeathBlock(self.headformat, self.headfields, self.Info.ConditionVals, "", [50, 40],
											 self.CharColor, False, True, extra={'LABEL': self.scrlabel})]
			h = renderedlines[-1].get_height()
			if conditions:
				renderedlines.append(weatherinfo.CreateWeathBlock(self.condformat,self.condfields,self.Info.ConditionVals,"",[45,25,35],self.CharColor, True,False))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(weatherinfo.CreateWeathBlock(self.dayformat,self.dayfields,self.Info.ConditionVals,"",30,self.CharColor, False, True))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(weatherinfo.CreateWeathBlock(self.footformat,self.footfields,self.Info.ConditionVals,"",25,self.CharColor, False, True))
				h = h + renderedlines[-1].get_height()
				s = (usefulheight - h) / (len(renderedlines) - 1) if len(renderedlines) > 1 else 0
				for l in renderedlines:
					config.screen.blit(l, ((config.screenwidth - l.get_width())/2, vert_off))
					vert_off = vert_off + l.get_height() + s

			else:
				fcstlines = 0
				maxfcstwidth = 0
				for fcst in self.Info.ForecastVals:
					renderedlines.append(weatherinfo.CreateWeathBlock(self.fcstformat,self.fcstfields,fcst,"",25,self.CharColor,True,False))
					if renderedlines[-1].get_width() > maxfcstwidth: maxfcstwidth = renderedlines[-1].get_width()
					fcstlines += 1

				if config.screenwidth > 350:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = (fcstlines + 1) / 2
					usewidth = config.screenwidth / 2
					lastfcst = 11
				else:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 5
					usewidth = config.screenwidth
					lastfcst = 6
				s = (usefulheight - h) / fcstlines

				config.screen.blit(renderedlines[0],((config.screenwidth - renderedlines[0].get_width())/2,vert_off))
				vert_off = vert_off + renderedlines[0].get_height() + s
				startvert = vert_off
				horiz_off = (usewidth - maxfcstwidth) / 2
				for dy, fcst in enumerate(renderedlines[1:lastfcst]):
					config.screen.blit(fcst, (horiz_off, vert_off))
					vert_off = vert_off + s + fcst.get_height()
					if (dy == 4) and (config.screenwidth > 350):
						horiz_off = horiz_off + usewidth
						vert_off = startvert

		pygame.display.update()

	def InitDisplay(self, nav):
		self.currentconditions = True
		super(WeatherScreenDesc, self).InitDisplay(nav)
		if self.ShowScreen(self.currentconditions) == -1:
			config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Weather screen error')

	def ExitScreen(self):
		pass

config.screentypes["Weather"] = WeatherScreenDesc
