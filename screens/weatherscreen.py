import pygame
import config
from debug import debugPrint
from stores import valuestore, weatherstore
import screen
import logsupport
from weatherfromatting import CreateWeathBlock, WFormatter
import utilities
import toucharea
from collections import OrderedDict
from utilities import wc

fsizes = ((20, False, False), (30, True, False), (45, True, True))
"""
num fcst days, 1 or 2 col, format override, spacing, block center, other params from timetemp?
default cols based on screen width > 390 use 2 col
def fcst days based on screen height?
for conditions where to put icon?  Center vertically? with size lesser of % of screen width % of screen height
"""

class WeatherScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		self.fmt = WFormatter()
		debugPrint('Screen', "New WeatherScreenDesc ", screenname)
		screen.ScreenDesc.__init__(self, screensection, screenname)
		butsize = screen.ButSize(1, 1, 0)
		self.Keys = OrderedDict({'condorfcst': toucharea.TouchPoint('condorfcst', (
		config.horizborder + .5*butsize[0], config.topborder + .5*butsize[1]), butsize,
																	proc=self.CondOrFcst)})
		self.currentconditions = True  # show conditions or forecast

		utilities.LocalizeParams(self, screensection, '-', 'WunderKey', location='')

		self.scrlabel = screen.FlatenScreenLabel(self.label)

		self.condformat = u"{d[0]} {d[1]}\u00B0F",u"  Feels like: {d[2]}\u00B0","Wind {d[3]}@{d[4]} gusts {d[5]}"
		self.condfields = list(((self.location, 'Cond', x) for x in ('Sky','Temp','Feels','WindDir', 'WindMPH', 'WindGust')))

		self.dayformat  = "Sunrise: {d[0]:02d}:{d[1]:02d}","Sunset:  {d[2]:02d}:{d[3]:02d}","Moon rise: {d[4]} set: {d[5]}","{d[6]}% illuminated"
		self.dayfields  = list(((self.location, 'Cond', x) for x in ('SunriseH','SunriseM','SunsetH','SunsetM','Moonrise','Moonset','MoonPct')))

		self.footformat = "Readings as of", "{d[0]} ago",
		self.footfields = ((self.location,'Cond','Age'),)

		self.fcstformat = u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}","Wind: {d[4]} at {d[5]}"
		self.fcstfields = list(((self.location, 'Fcst', x) for x in ('Day', 'High','Low', 'Sky', 'WindDir','WindSpd')))

		self.store = valuestore.NewValueStore(weatherstore.WeatherVals(self.location, self.WunderKey))
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

		if self.store.failedfetch:
			# todo fix this error screen
			renderedlines = [config.fonts.Font(45, "").render(self.fmt.format("{d[0]}",'Weather Not Available',
															d=self.scrlabel), 0, wc(self.CharColor))]
			for l in renderedlines:
				config.screen.blit(l, ((config.screenwidth - l.get_width()) / 2, vert_off))
				vert_off = vert_off + 30
			logsupport.Logs.Log('Weatherscreen missing weather' + self.name, severity=logsupport.ConsoleWarning)
		else:
			renderedlines = [config.fonts.Font(50, "").render(self.fmt.format("{d}",d=self.scrlabel),0,wc(self.CharColor))]
			renderedlines.append(config.fonts.Font(40, "").render(self.fmt.format("{d}",d=self.store.GetVal(('Cond','Location'))),0,wc(self.CharColor)))

			h = renderedlines[0].get_height() + renderedlines[1].get_height()
			if conditions:
				renderedlines.append(CreateWeathBlock(self.condformat, self.condfields, "", [45, 25, 35], self.CharColor, (self.location, 'Cond', 'Icon'), False))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(CreateWeathBlock(self.dayformat, self.dayfields, "", [30], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(CreateWeathBlock(self.footformat, self.footfields, "", [25], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				s = (usefulheight - h) / (len(renderedlines) - 1) if len(renderedlines) > 1 else 0
				for l in renderedlines:
					config.screen.blit(l, ((config.screenwidth - l.get_width())/2, vert_off))
					vert_off = vert_off + l.get_height() + s

			else:
				fcstlines = 0
				maxfcstwidth = 0
				for i in range(10):
					renderedlines.append(CreateWeathBlock(self.fcstformat, self.fcstfields, "", [25], self.CharColor, (self.location, 'Fcst', 'Icon'), False, day=i))
					if renderedlines[-1].get_width() > maxfcstwidth: maxfcstwidth = renderedlines[-1].get_width()
					fcstlines += 1

				if config.screenwidth > 350:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 2 + (fcstlines + 1) / 2
					usewidth = config.screenwidth / 2
					lastfcst = 12
				else:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 5
					usewidth = config.screenwidth
					lastfcst = 7
				s = (usefulheight - h) / (fcstlines -1)

				config.screen.blit(renderedlines[0],((config.screenwidth - renderedlines[0].get_width())/2,vert_off))
				vert_off = vert_off + renderedlines[0].get_height() + s
				config.screen.blit(renderedlines[1],
								   ((config.screenwidth - renderedlines[1].get_width()) / 2, vert_off))
				vert_off = vert_off + renderedlines[1].get_height() + s
				startvert = vert_off
				horiz_off = (usewidth - maxfcstwidth) / 2
				for dy, fcst in enumerate(renderedlines[2:lastfcst]):
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
