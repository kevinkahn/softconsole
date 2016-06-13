import time

import pygame
import webcolors

import config
from config import debugPrint, WAITEXTRACONTROLBUTTON, WAITEXIT

wc = webcolors.name_to_rgb
import screen
import logsupport
import weatherinfo
import utilities

fsizes = ((20, False, False), (30, True, False), (45, True, True))


class WeatherScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('BuildScreen', "New WeatherScreenDesc ", screenname)

		screen.ScreenDesc.__init__(self, screensection, screenname, (('which',('',)),))
		utilities.LocalizeParams(self, screensection, WunderKey='', location='')
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		# entries are (fontsize, centered, formatstring, values)
		self.conditions = [(2, True, "{d}", self.scrlabel),
						   (1, True, "{d[0]}", ('Location',)),
						   (1, False, u"Now: {d[0]} {d[1]}\u00B0F", ('Sky', 'Temp')),
						   (0, False, u"  Feels like: {d[0]}\u00B0", ('Feels',)),
						   (1, False, "Wind {d[0]}", ('WindStr',)),
						   (1, False, "Sunrise: {d[0]:02d}:{d[1]:02d}", ('SunriseH', 'SunriseM')),
						   (1, False, "Sunset:  {d[0]:02d}:{d[1]:02d}", ('SunsetH', 'SunsetM')),
						   (0, False, "Moon rise: {d[0]} set: {d[1]}", ('Moonrise', 'Moonset')),
						   (0, False, "     {d[0]}% illuminated", ('MoonPct',)),
						   (0, False, "will be replaced", "")]
		self.forecast = [(1, False, u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}", ('Day', 'High', 'Low', 'Sky')),
						 (1, False, "Wind: {d[0]} at {d[1]}", ('WindDir', 'WindSpd'))]
		self.Info = weatherinfo.WeatherInfo(self.WunderKey, self.location)
		utilities.register_example("WeatherScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     WeatherScreenDesc:" + str(self.CharColor)

	def RenderScreenLines(self, recipe, values, color):
		h = 0
		renderedlines = []
		centered = []
		linetorender = ""
		for line in recipe:
			try:
				if isinstance(line[3], basestring):  # handles case of a direct var e.g. label string
					linestr = line[2].format(d=line[3])
				else:
					args = []
					for item in line[3]:
						args.append(values[item])
					linestr = line[2].format(d=args)
			except:
				config.Logs.Log("Weather format error: " + str(line[3]), severity=logsupport.ConsoleWarning)
				linestr = ''
			r = config.fonts.Font(fsizes[line[0]][0], '', fsizes[line[0]][1], fsizes[line[0]][2]).render(
				linetorender + linestr, 0, wc(color))
			linetorender = ""
			renderedlines.append(r)
			centered.append(line[1])
			h = h + r.get_height()
		return renderedlines, centered, h



	def ShowScreen(self, conditions):
		self.PaintBase([[('Conditions',)], [('Forecast',)]][conditions])
		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		centered = []
		if self.Info.FetchWeather() == -1:
			return -1
		if conditions:
			self.conditions[-1] = (0, False, "Readings as of {d} ago", self.Info.ConditionVals['Age'])
			renderedlines, centered, h = self.RenderScreenLines(self.conditions, self.Info.ConditionVals,
																self.CharColor)
		else:
			renderedlines = [config.fonts.Font(fsizes[2][0], '', fsizes[2][1], fsizes[2][2]).render(self.scrlabel, 0,
																									wc(self.CharColor))]
			centered.append(True)
			h = h + renderedlines[0].get_height()
			for fcst in self.Info.ForecastVals:
				r, c, temph = self.RenderScreenLines(self.forecast, fcst, self.CharColor)
				h += temph
				renderedlines = renderedlines + r
				centered = centered + c

		s = (usefulheight - h)/(len(renderedlines) - 1) if len(renderedlines) > 1 else 0
		vert_off = config.topborder

		for i in range(len(renderedlines)):
			if centered[i]:
				horiz_off = (config.screenwidth - renderedlines[i].get_width())/2
			else:
				horiz_off = config.horizborder
			config.screen.blit(renderedlines[i], (horiz_off, vert_off))
			vert_off = vert_off + renderedlines[i].get_height() + s
		pygame.display.update()

	def HandleScreen(self, newscr=True):

		# stop any watching for device stream
		config.toDaemon.put([])
		currentconditions = True
		if self.ShowScreen(currentconditions) == -1:
			return config.HomeScreen
		while 1:
			choice = config.DS.NewWaitPress(self)
			if choice[0] == WAITEXIT:
				return choice[1]
			elif choice[0] == WAITEXTRACONTROLBUTTON:
				currentconditions = not currentconditions
				self.ShowScreen(currentconditions)


config.screentypes["Weather"] = WeatherScreenDesc
