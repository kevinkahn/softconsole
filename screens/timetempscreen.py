import time

import pygame

import debug
import fonts
import hw
import logsupport
import screen
import screens.__screens as screens
from logsupport import ConsoleWarning
from stores import valuestore
from utilfuncs import wc, fmt
from weatherfromatting import CreateWeathBlock


def extref(listitem, indexitem):
	try:
		return listitem[indexitem]
	except IndexError:
		return listitem[-1]


class TimeTempScreenDesc(screen.ScreenDesc):

	def __init__(self, screensection, screenname, Clocked=0):
		# time temp screens clock once per second
		super().__init__(screensection, screenname, Clocked=1)
		debug.debugPrint('Screen', "New TimeTempDesc ", screenname)

		screen.AddUndefaultedParams(self, screensection, location='', CharSize=[-1],
									ClockSize=-1, LocationSize=-1, CondSize=[20], FcstSize=[20],
									Font=fonts.monofont, FcstLayout='Block',
									FcstIcon=True, CondIcon=True,
									TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
									ForecastFormat=[], ForecastDays=1, SkipDays=0, IconSizePct=100)
		if self.CharSize != [-1]:
			# old style
			logsupport.Logs.Log(
				"TimeTemp screen CharSize parameter deprecated, change to specific block size parameters",
				severity=ConsoleWarning)
			self.ClockSize = extref(self.CharSize, 0)
			self.LocationSize = extref(self.CharSize, 1)
			self.CondSize = extref(self.CharSize, 2)
			self.FcstSize = extref(self.CharSize, 3)
		if self.ForecastDays + self.SkipDays > 10:
			self.ForecastDays = 10 - self.SkipDays
			logsupport.Logs.Log("Long forecast requested; days reduced to: " + str(self.ForecastDays),
								severity=ConsoleWarning)
		if self.FcstLayout not in ('Block', 'BlockCentered', 'LineCentered', '2ColVert', '2ColHoriz'):
			logsupport.Logs.Log(
				'FcstLayout Param not Block, BlockCentered, LineCentered, 2ColVert, or 2ColHoriz - using "Block" for ',
				screenname, severity=ConsoleWarning)
			self.FcstLayout = "Block"
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		try:
			self.store = valuestore.ValueStores[self.location]
		except KeyError:
			logsupport.Logs.Log("Timetemp screen {} using non-existent location {}".format(screenname, self.location),
								severity=ConsoleWarning)
			raise ValueError
		self.DecodedCondFields = []
		for f in self.ConditionFields:
			if ':' in f:
				self.DecodedCondFields.append(f.split(':'))
			else:
				self.DecodedCondFields.append((self.location, 'Cond', f))

		self.condicon = (self.location, 'Cond', 'Icon') if self.CondIcon else None

		self.DecodedFcstFields = []
		for f in self.ForecastFields:
			if ':' in f:
				self.DecodedFcstFields.append(f.split(':'))
			else:
				self.DecodedFcstFields.append((self.location, 'Fcst', f))
		self.fcsticon = (self.location, 'Fcst', 'Icon') if self.FcstIcon else None

	def InitDisplay(self, nav):
		super(TimeTempScreenDesc, self).InitDisplay(nav)

	def ReInitDisplay(self):
		super().ReInitDisplay()

	def ScreenContentRepaint(self):
		if not self.Active: return  # handle race condition where repaint queued just before switch
		h = 0
		renderedforecast = []
		sizeindex = 0
		renderedtime = []
		renderedtimelabel = []

		tw = 0
		for i in range(len(self.TimeFormat)):
			renderedtime.append(fonts.fonts.Font(self.ClockSize, self.Font).render(
				time.strftime(self.TimeFormat[i]), 0, wc(self.CharColor)))
			h = h + renderedtime[-1].get_height()
			if renderedtime[-1].get_width() > tw: tw = renderedtime[-1].get_width()
			sizeindex += 1
		renderedtimelabel.append(pygame.Surface((tw, h)))
		renderedtimelabel[-1].set_colorkey(wc('black'))
		v = 0
		for l in renderedtime:
			renderedtimelabel[0].blit(l, (((tw - l.get_width()) / 2), v))
			v = v + l.get_height()
		spaces = 1

		if self.LocationSize != 0:
			renderedtimelabel.append(
				fonts.fonts.Font(self.LocationSize, self.Font).render(
					fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)))
			h = h + renderedtimelabel[-1].get_height()
			spaces += 1
		sizeindex += 1

		if not self.store.ValidWeather:
			maxh = hw.screenwidth + 10
			fontsize = 30
			while maxh > hw.screenwidth:
				renderedlines = [
					fonts.fonts.Font(fontsize, self.Font).render(x, 0, wc(self.CharColor)) for x in self.store.Status]
				maxh = max([x.get_width() for x in renderedlines])
				fontsize = fontsize - 2

			vert_off = self.startvertspace
			for tmlbl in renderedtimelabel:
				horiz_off = (hw.screenwidth - tmlbl.get_width()) / 2
				hw.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + 20 + tmlbl.get_height()
			for l in renderedlines:
				hw.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, vert_off))
				vert_off += l.get_height()
		else:
			cb = CreateWeathBlock(self.ConditionFormat, self.DecodedCondFields, self.Font,
								  self.CondSize, self.CharColor, self.condicon,
								  self.FcstLayout == 'LineCentered',
								  maxiconsize=round(self.IconSizePct / 100 * self.useablehorizspace),
								  maxhorizwidth=self.useablehorizspace)
			h = h + cb.get_height()

			if self.FcstLayout in ('2ColVert', '2ColHoriz'):
				screenmaxfcstwidth = self.useablehorizspace // 2 - 10
			else:
				screenmaxfcstwidth = self.useablehorizspace

			maxfcstwidth = 0
			forecastlines = 0
			maxfcstheight = 0
			spaces += 1
			maxfcsticon = round(self.IconSizePct / 100 * self.useablehorizspace / (
				2 if self.FcstLayout in ('2ColVert', '2ColHoriz') else 1))
			for dy in range(self.ForecastDays):
				fb = CreateWeathBlock(self.ForecastFormat, self.DecodedFcstFields, self.Font,
									  self.FcstSize, self.CharColor, self.fcsticon,
									  self.FcstLayout == 'LineCentered', day=dy + self.SkipDays,
									  maxiconsize=maxfcsticon, maxhorizwidth=screenmaxfcstwidth)
				renderedforecast.append(fb)
				if fb.get_width() > maxfcstwidth: maxfcstwidth = fb.get_width()
				if fb.get_height() > maxfcstheight: maxfcstheight = fb.get_height()
				forecastlines += 1


			if self.FcstLayout in ('2ColVert', '2ColHoriz'):
				h = h + maxfcstheight * ((self.ForecastDays + 1) // 2)
				forecastlines = (forecastlines + 1) // 2
				usewidth = hw.screenwidth // 2
			else:
				h = h + maxfcstheight * self.ForecastDays
				usewidth = hw.screenwidth

			s = max((self.useablevertspace - h) / (spaces + forecastlines - 1), 0)  # gap between blocks to use
			extraspace = max((self.useablevertspace - h - s * (spaces + forecastlines - 1)) / spaces,
							 0)  # round off gap space - use before fcsts

			vert_off = self.startvertspace
			for tmlbl in renderedtimelabel:
				horiz_off = (hw.screenwidth - tmlbl.get_width()) // 2
				hw.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + s + tmlbl.get_height()

			hw.screen.blit(cb, ((hw.screenwidth - cb.get_width()) // 2, vert_off))
			vert_off = vert_off + s + cb.get_height() + extraspace

			startvert = vert_off
			maxvert = startvert
			fcstvert = maxfcstheight
			horiz_off = (usewidth - maxfcstwidth) // 2
			for dy, fcst in enumerate(renderedforecast):
				h_off = horiz_off
				v_off = vert_off
				if self.FcstLayout == '2ColHoriz':
					h_off = horiz_off + (dy % 2) * usewidth
					vert_off = vert_off + (dy % 2) * (s + fcstvert)
				elif self.FcstLayout == '2ColVert':
					vert_off = vert_off + s + fcstvert
					if dy == (self.ForecastDays + 1) // 2 - 1:
						horiz_off = horiz_off + usewidth
						vert_off = startvert
				elif self.FcstLayout in ('BlockCentered', 'LineCentered'):
					vert_off = vert_off + s + fcstvert
					h_off = (usewidth - fcst.get_width()) // 2
				else:
					vert_off = vert_off + s + fcstvert
				if v_off > maxvert: maxvert = v_off
				hw.screen.blit(fcst, (h_off, v_off))

			if self.FcstLayout == '2ColVert': pygame.draw.line(hw.screen, wc('white'),
															   (usewidth, startvert + fcstvert // 3),
															   (usewidth, maxvert + 2 * fcstvert / 3))

screens.screentypes["TimeTemp"] = TimeTempScreenDesc
