import pygame
import config
import debug
import fonts
import hw
import screens.__screens as screens
from stores import valuestore
import screen
import logsupport
from weatherfromatting import CreateWeathBlock, WFormatter
import utilities
import toucharea
from collections import OrderedDict
from utilfuncs import wc

fsizes = ((20, False, False), (30, True, False), (45, True, True))

class WeatherScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "New WeatherScreenDesc ", screenname)
		screen.ScreenDesc.__init__(self, screensection, screenname)

		self.fmt = WFormatter()

		butsize = screen.ButSize(1, 1, 0)
		self.Keys = OrderedDict({'condorfcst': toucharea.TouchPoint('condorfcst', (
			screens.horizborder + .5 * butsize[0], screens.topborder + .5 * butsize[1]), butsize,
																	proc=self.CondOrFcst)})
		self.currentconditions = True  # show conditions or forecast
		screen.AddUndefaultedParams(self, screensection, location='', LocationSize=40)

		self.scrlabel = screen.FlatenScreenLabel(self.label)

		self.condformat = u"{d[0]} {d[1]}\u00B0F", u"  Feels like: {d[2]}\u00B0", "Wind {d[3]}@{d[4]}"
		self.condfields = list(((self.location, 'Cond', x) for x in ('Sky', 'Temp', 'Feels', 'WindDir', 'WindMPH')))

		# self.dayformat  = "Sunrise: {d[0]:02d}:{d[1]:02d}","Sunset:  {d[2]:02d}:{d[3]:02d}","Moon rise: {d[4]} set: {d[5]}","{d[6]}% illuminated"
		# self.dayfields  = list(((self.location, 'Cond', x) for x in ('SunriseH','SunriseM','SunsetH','SunsetM','Moonrise','Moonset','MoonPct')))
		self.dayformat = "Sunrise: {d[0]}", "Sunset:  {d[1]}", "Moon rise: {d[2]} set: {d[3]}"
		self.dayfields = list(((self.location, 'Cond', x) for x in ('Sunrise', 'Sunset', 'Moonrise', 'Moonset')))

		self.footformat = "Readings as of {d[0]}",
		self.footfields = ((self.location,'Cond','Age'),)

		self.fcstformat = u"{d[0]}   {d[1]}\u00B0/{d[2]}\u00B0 {d[3]}", "Wind: {d[4]}"
		self.fcstfields = list(((self.location, 'Fcst', x) for x in ('Day', 'High', 'Low', 'Sky', 'WindSpd')))

		try:
			self.store = valuestore.ValueStores[self.location]
		except KeyError:
			logsupport.Logs.Log("Weather screen {} using non-existent location {}".format(screenname, self.location), severity = logsupport.ConsoleWarning)
			raise ValueError
		self.loggedonce = False
		utilities.register_example("WeatherScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     WeatherScreenDesc:" + str(self.CharColor)

	# noinspection PyUnusedLocal
	def CondOrFcst(self, press):
		self.currentconditions = not self.currentconditions
		self.ShowScreen(self.currentconditions)

	def ShowScreen(self, conditions):
		self.ReInitDisplay()
		self.store.BlockRefresh()

		usefulheight = hw.screenheight - screens.topborder - screens.botborder
		vert_off = screens.topborder

		if self.store.failedfetch:
			renderedlines = [
				fonts.fonts.Font(50, "").render(self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)),
				fonts.fonts.Font(45, "").render('Weather Not Available', 0, wc(self.CharColor))]
			for l in renderedlines:
				config.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, vert_off))
				vert_off = vert_off + 60
			if not self.loggedonce:
				logsupport.Logs.Log('Weatherscreen missing weather ' + self.name, severity=logsupport.ConsoleWarning)
				self.loggedonce = True
		else:
			self.loggedonce = False
			renderedlines = [fonts.fonts.Font(50, "").render(self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor))]
			h = renderedlines[0].get_height()
			if self.LocationSize != 0:
				renderedlines.append(
				fonts.fonts.Font(self.LocationSize, "").render(self.fmt.format("{d}", d=self.store.GetVal(('Cond', 'Location'))), 0,
												wc(self.CharColor)))
				h = h + renderedlines[1].get_height()
			if conditions:
				renderedlines.append(CreateWeathBlock(self.condformat, self.condfields, "", [45, 25, 35], self.CharColor, (self.location, 'Cond', 'Icon'), False))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(CreateWeathBlock(self.dayformat, self.dayfields, "", [30], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				renderedlines.append(CreateWeathBlock(self.footformat, self.footfields, "", [25], self.CharColor, None, True))
				h = h + renderedlines[-1].get_height()
				s = (usefulheight - h) / (len(renderedlines) - 1) if len(renderedlines) > 1 else 0
				for l in renderedlines:
					config.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, vert_off))
					vert_off = vert_off + l.get_height() + s

			else:
				fcstlines = 0
				fcstdays = valuestore.GetVal((self.location, 'FcstDays'))
				maxfcstwidth = 0
				if fcstdays > 0:
					for i in range(fcstdays):
						renderedlines.append(
							CreateWeathBlock(self.fcstformat, self.fcstfields, "", [25], self.CharColor,
											 (self.location, 'Fcst', 'Icon'), False, day=i))
						if renderedlines[-1].get_width() > maxfcstwidth: maxfcstwidth = renderedlines[-1].get_width()
						fcstlines += 1
				else:
					renderedlines.append(fonts.fonts.Font(35, "").render("No Forecast Available", 0,
																		 wc(self.CharColor)))

				if hw.screenwidth > 350:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 2 + (fcstlines + 1) / 2
					usewidth = hw.screenwidth / 2
					lastfcst = 12
				else:
					h = h + renderedlines[-1].get_height() * 5
					fcstlines = 5
					usewidth = hw.screenwidth
					lastfcst = 7
				s = (usefulheight - h) / (fcstlines+1)

				config.screen.blit(renderedlines[0], ((hw.screenwidth - renderedlines[0].get_width()) / 2, vert_off))
				vert_off = vert_off + renderedlines[0].get_height() + s
				config.screen.blit(renderedlines[1],
								   ((hw.screenwidth - renderedlines[1].get_width()) / 2, vert_off))
				vert_off = vert_off + renderedlines[1].get_height() + s
				startvert = vert_off
				horiz_off = (usewidth - maxfcstwidth) / 2
				for dy, fcst in enumerate(renderedlines[2:lastfcst]):
					config.screen.blit(fcst, (horiz_off, vert_off))
					vert_off = vert_off + s + fcst.get_height()
					if (dy == 4) and (hw.screenwidth > 350):
						horiz_off = horiz_off + usewidth
						vert_off = startvert

		pygame.display.update()

	def InitDisplay(self, nav):
		self.currentconditions = True
		super(WeatherScreenDesc, self).InitDisplay(nav)
		if self.ShowScreen(
				self.currentconditions) == -1:  # todo should remove since errors are caught now in switch screen
			config.DS.SwitchScreen(screens.HomeScreen, 'Bright', 'Home', 'Weather screen error')

	def ExitScreen(self):
		pass


screens.screentypes["Weather"] = WeatherScreenDesc
