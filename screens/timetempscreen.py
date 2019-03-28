import time

import config
import fonts
import hw
import screen
import debug
import screens.__screens as screens
from utilfuncs import wc
from stores import valuestore
from weatherfromatting import CreateWeathBlock, WFormatter
import pygame
import logsupport
from logsupport import ConsoleWarning
from timers import RepeatingPost


def extref(listitem, indexitem):
	try:
		return listitem[indexitem]
	except IndexError:
		return listitem[-1]

class TimeTempScreenDesc(screen.ScreenDesc):
	# todo rethink title for these screens as it appears below the clock

	def __init__(self, screensection, screenname):
		# todo change to use screen title
		screen.ScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "New TimeTempDesc ", screenname)

		screen.AddUndefaultedParams(self, screensection, location='', CharSize=[-1],
									ClockSize=-1, LocationSize=-1, CondSize=[20], FcstSize=[20],
									Font=fonts.monofont, FcstLayout='Block',
									FcstIcon=True, CondIcon=True,
									TimeFormat=[], ConditionFields=[], ConditionFormat=[], ForecastFields=[],
									ForecastFormat=[], ForecastDays=1, SkipDays=0)

		if self.CharSize != [-1]:
			# old style
			logsupport.Logs.Log("TimeTemp screen CharSize parameter deprecated, change to specific block size parameters", severity=ConsoleWarning)
			self.ClockSize = extref(self.CharSize, 0)
			self.LocationSize = extref(self.CharSize, 1)
			self.CondSize = extref(self.CharSize, 2)
			self.FcstSize = extref(self.CharSize, 3)
		if self.ForecastDays + self.SkipDays > 10:
			self.ForecastDays = 10 - self.SkipDays
			logsupport.Logs.Log("Long forecast requested; days reduced to: "+str(self.ForecastDays),severity=ConsoleWarning)
		if self.FcstLayout not in ('Block','BlockCentered','LineCentered','2ColVert','2ColHoriz'):
			logsupport.Logs.Log('FcstLayout Param not Block, BlockCentered, LineCentered, 2ColVert, or 2ColHoriz - using "Block" for ' ,
							screenname,severity=ConsoleWarning)
			self.FcstLayout = "Block"
		self.scrlabel = screen.FlatenScreenLabel(self.label)
		try:
			self.store = valuestore.ValueStores[self.location]
		except KeyError:
			logsupport.Logs.Log("Timetemp screen {} using non-existent location {}".format(screenname, self.location), severity = ConsoleWarning)
			raise ValueError
		self.DecodedCondFields = []
		for f in self.ConditionFields:
			if ':' in f:
				self.DecodedCondFields.append(f.split(':'))
			else:
				self.DecodedCondFields.append((self.location,'Cond',f))

		self.condicon = (self.location,'Cond','Icon') if self.CondIcon else None

		self.DecodedFcstFields = []
		for f in self.ForecastFields:
			if ':' in f:
				self.DecodedFcstFields.append(f.split(':'))
			else:
				self.DecodedFcstFields.append((self.location,'Fcst',f))
		self.fcsticon = (self.location,'Fcst','Icon') if self.FcstIcon else None

		self.poster = RepeatingPost(1.0,paused=True, name=self.name,proc=self.repaintClock)
		self.poster.start()
		self.fmt = WFormatter()

	def InitDisplay(self, nav):
		super(TimeTempScreenDesc, self).InitDisplay(nav)
		self.repaintClock()
		self.poster.resume()

	def ExitScreen(self):
		self.poster.pause()
		super(TimeTempScreenDesc, self).ExitScreen()

	def repaintClock(self, param=None):
		if not self.Active: return # handle race condition where repaint queued just before switch
		h = 0
		renderedforecast  = []
		sizeindex = 0
		renderedtime = []
		renderedtimelabel = []

		self.store.BlockRefresh()


		tw = 0
		for i in range(len(self.TimeFormat)):
			renderedtime.append(fonts.fonts.Font(self.ClockSize, self.Font).render(
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

		if self.LocationSize != 0:
			renderedtimelabel.append(
				fonts.fonts.Font(self.LocationSize, self.Font).render(
					self.fmt.format("{d}", d=self.scrlabel), 0, wc(self.CharColor)))
			h = h + renderedtimelabel[-1].get_height()
			spaces += 1
		sizeindex += 1

		if self.store.failedfetch:
			errmsg1 = fonts.fonts.Font(self.LocationSize, self.Font).render('Weather', 0, wc(self.CharColor))
			errmsg2 = fonts.fonts.Font(self.LocationSize, self.Font).render('unavailable', 0, wc(self.CharColor))
			errmsg3 = fonts.fonts.Font(self.LocationSize, self.Font).render('or error', 0, wc(self.CharColor))
			#self.PaintBase()
			vert_off = screens.topborder
			self.ReInitDisplay()
			for tmlbl in renderedtimelabel:
				horiz_off = (hw.screenwidth - tmlbl.get_width()) / 2
				config.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + 20 + tmlbl.get_height()
			config.screen.blit(errmsg1, ((hw.screenwidth - errmsg1.get_width()) / 2, vert_off))
			config.screen.blit(errmsg2, ((hw.screenwidth - errmsg2.get_width()) / 2, vert_off + errmsg1.get_height()))
			config.screen.blit(errmsg3,
							   ((hw.screenwidth - errmsg3.get_width()) / 2, vert_off + 2 * errmsg1.get_height()))
		else:
			cb = CreateWeathBlock(self.ConditionFormat, self.DecodedCondFields,self.Font,
								  self.CondSize,self.CharColor,self.condicon,
								  self.FcstLayout == 'LineCentered')
			h = h + cb.get_height()

			maxfcstwidth = 0
			forecastlines = 0
			spaces += 1
			for dy in range(self.ForecastDays):
				fb = CreateWeathBlock(self.ForecastFormat, self.DecodedFcstFields,self.Font,
									  self.FcstSize, self.CharColor, self.fcsticon,
									  self.FcstLayout == 'LineCentered',day=dy + self.SkipDays)
				renderedforecast.append(fb)
				if fb.get_width() > maxfcstwidth: maxfcstwidth = fb.get_width()
				forecastlines += 1
			forecastitemheight = renderedforecast[-1].get_height()

			if self.FcstLayout in ('2ColVert','2ColHoriz'):
				h = h + forecastitemheight * ((self.ForecastDays + 1) // 2)
				forecastlines = (forecastlines + 1) // 2
				usewidth = hw.screenwidth // 2
			else:
				h = h + forecastitemheight * self.ForecastDays
				usewidth = hw.screenwidth

			s = (self.useablevertspace - h)/(spaces + forecastlines - 1)
			extraspace = (self.useablevertspace - h - s*(spaces + forecastlines - 1))/spaces

			vert_off = self.startvertspace
			self.ReInitDisplay()
			for tmlbl in renderedtimelabel:
				horiz_off = (hw.screenwidth - tmlbl.get_width()) // 2
				config.screen.blit(tmlbl, (horiz_off, vert_off))
				vert_off = vert_off + s + tmlbl.get_height() + extraspace

			config.screen.blit(cb, ((hw.screenwidth - cb.get_width()) // 2, vert_off))
			vert_off = vert_off + s + cb.get_height() + extraspace

			startvert = vert_off
			maxvert = startvert
			fcstvert = renderedforecast[0].get_height()
			horiz_off = (usewidth - maxfcstwidth) // 2
			for dy,fcst in enumerate(renderedforecast):
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
					h_off = (usewidth - fcst.get_width())//2
				else:
					vert_off = vert_off + s + fcstvert
				if v_off > maxvert: maxvert = v_off
				config.screen.blit(fcst, (h_off, v_off))

			if self.FcstLayout == '2ColVert': pygame.draw.line(config.screen,wc('white'),(usewidth,startvert+fcstvert//3),(usewidth,maxvert + 2*fcstvert/3))

		pygame.display.update()

		#config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)


screens.screentypes["TimeTemp"] = TimeTempScreenDesc
