from collections import OrderedDict

import pygame

import functools
import debug
import fonts
import hw
import logsupport
import screen
import screens.__screens as screens
import toucharea
import utilities
from stores import valuestore
from utilfuncs import wc
from weatherfromatting import CreateWeathBlock, WFormatter

fsizes = ((20, False, False), (30, True, False), (45, True, True))


class WeatherScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname, Clocked=0):
		debug.debugPrint('Screen', "New WeatherScreenDesc ", screenname)
		super().__init__(screensection, screenname, Clocked=Clocked)

		self.fmt = WFormatter()

		butsize = self.ButSize(1, 1, 0)
		self.Keys = OrderedDict({'condorfcst': toucharea.TouchPoint('condorfcst', (
			self.HorizBorder + .5 * butsize[0], self.TopBorder + .5 * butsize[1]), butsize,
																	proc=self.CondOrFcst)})
		self.currentconditions = True  # show conditions or forecast
		screen.AddUndefaultedParams(self, screensection, location='',
									LocationSize=0)  # default to no location now that screen title in use

		self.SetScreenTitle(screen.FlatenScreenLabel(self.label), 50, self.CharColor)

		self.condformat = u"{d[0]} {d[1]}\u00B0F", u"  Feels like: {d[2]}\u00B0", "Wind {d[3]}@{d[4]}"
		self.condfields = list(((self.location, 'Cond', x) for x in ('Sky', 'Temp', 'Feels', 'WindDir', 'WindMPH')))

		# self.dayformat  = "Sunrise: {d[0]:02d}:{d[1]:02d}","Sunset:  {d[2]:02d}:{d[3]:02d}","Moon rise: {d[4]} set: {d[5]}","{d[6]}% illuminated"
		# self.dayfields  = list(((self.location, 'Cond', x) for x in ('SunriseH','SunriseM','SunsetH','SunsetM','Moonrise','Moonset','MoonPct')))
		self.dayformat = "Sunrise: {d[0]}", "Sunset:  {d[1]}"  # , "Moon rise: {d[2]} set: {d[3]}"
		self.dayfields = list(((self.location, 'Cond', x) for x in ('Sunrise', 'Sunset')))  # , 'Moonrise', 'Moonset')))

		self.footformat = "Readings as of {d[0]}",
		self.footfields = ((self.location, 'Cond', 'Age'),)

		self.fcstformat = u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}", "Wind: {d[4]}"
		self.fcstfields = list(((self.location, 'Fcst', x) for x in ('Day', 'High', 'Low', 'Sky', 'WindSpd')))

		try:
			self.store = valuestore.ValueStores[self.location]
		except KeyError:
			logsupport.Logs.Log("Weather screen {} using non-existent location {}".format(screenname, self.location),
								severity=logsupport.ConsoleWarning)
			raise ValueError
		utilities.register_example("WeatherScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     WeatherScreenDesc:" + str(self.CharColor)

	# noinspection PyUnusedLocal
	def CondOrFcst(self):
		self.currentconditions = not self.currentconditions
		self.ReInitDisplay()

	def ShowScreen(self, conditions):
		# todo given the useable vert space change should check for overflow or auto size font

		FreshData = self.store.BlockRefresh()  # use this to control repain?

		vert_off = self.startvertspace

		if not self.store.ValidWeather:
			renderedlines = [
				fonts.fonts.Font(45, "").render(x, 0, wc(self.CharColor)) for x in self.store.Status]
			for l in renderedlines:
				hw.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, vert_off))
				vert_off = vert_off + 60  # todo use useable space stuff and vert start
		else:
			renderedlines = []

			if self.LocationSize != 0:
				locblk = fonts.fonts.Font(self.LocationSize, "").render(
					self.fmt.format("{d}", d=self.store.GetVal(('Cond', 'Location'))), 0,
					wc(self.CharColor))
				hw.screen.blit(locblk, ((hw.screenwidth - locblk.get_width()) / 2, vert_off))
				vert_off = vert_off + locblk.get_height() + 10  # todo gap of 10 pixels is arbitrary

			h = vert_off
			if conditions:  # todo add max width and wrap
				renderedlines.append(
					CreateWeathBlock(self.condformat, self.condfields, "", [45, 25, 35], self.CharColor,
									 (self.location, 'Cond', 'Icon'), False))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(
					CreateWeathBlock(self.dayformat, self.dayfields, "", [30], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(
					CreateWeathBlock(self.footformat, self.footfields, "", [25], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				s = (self.useablevertspace - h) / (len(renderedlines) - 1) if len(renderedlines) > 1 else 0
				for l in renderedlines:
					hw.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, vert_off))
					vert_off = vert_off + l.get_height() + s

			else:
				fcstlines = 0
				if hw.screenwidth > 350:
					screenmaxfcstwidth = self.useablehorizspace // 2 - 10
				else:
					screenmaxfcstwidth = self.useablehorizspace
				fcstdays = valuestore.GetVal((self.location, 'FcstDays'))
				maxfcstwidth = 0
				maxfcstheight = 0
				if fcstdays > 0:
					for i in range(fcstdays):
						renderedlines.append(
							CreateWeathBlock(self.fcstformat, self.fcstfields, "", [25], self.CharColor,
											 # todo compute font size based on useable
											 (self.location, 'Fcst', 'Icon'), False, day=i,
											 maxhorizwidth=screenmaxfcstwidth))
						if renderedlines[-1].get_width() > maxfcstwidth: maxfcstwidth = renderedlines[-1].get_width()
						if renderedlines[-1].get_height() > maxfcstheight: maxfcstheight = renderedlines[
							-1].get_height()
						fcstlines += 1
				else:
					renderedlines.append(fonts.fonts.Font(35, "").render("No Forecast Available", 0,
																		 wc(self.CharColor)))

				if hw.screenwidth > 350:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 2 + (fcstlines + 1) / 2
					usewidth = hw.screenwidth / 2
				else:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 5
					usewidth = hw.screenwidth
				s = (self.useablevertspace - h) / (fcstlines + 1)

				startvert = vert_off
				horiz_off = (usewidth - maxfcstwidth) / 2
				for dy, fcst in enumerate(renderedlines):
					hw.screen.blit(fcst, (horiz_off, vert_off))
					vert_off = vert_off + s + maxfcstheight
					if (dy == 3) and (hw.screenwidth > 350):
						horiz_off = horiz_off + usewidth
						vert_off = startvert

	def InitDisplay(self, nav, specificrepaint = None):
		self.currentconditions = True
		Show = functools.partial(self.ShowScreen, self.currentconditions)
		super().InitDisplay(nav, specificrepaint=Show)

	def ReInitDisplay(self, specificrepaint = None):
		Show = functools.partial(self.ShowScreen, self.currentconditions)
		super().ReInitDisplay(specificrepaint=Show)

screens.screentypes["Weather"] = WeatherScreenDesc
