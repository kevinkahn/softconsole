from utilities import wc
import config
import time
import pygame
import debug
import screen
import utilities
from eventlist import ProcEventItem
import logsupport
from logsupport import ConsoleWarning
from weatherfromatting import CreateWeathBlock


class ClockScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		self.CharSize=[0]
		self.Font=''
		self.OutFormat=[]
		self.ExtraFields=[]
		self.ExtraFormat=[]
		self.ExtraSize=[]


		debug.debugPrint('Screen', "Build Clock Screen")
		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', CharSize=[20], Font=config.monofont, OutFormat=[],ExtraFields=[],
								 ExtraSize=[0], ExtraFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.KeyList = None  # no touch areas active on this screen
		utilities.register_example("ClockScreen", self)
		self.ClockRepaintEvent = ProcEventItem(id(self), 'clockrepaint', self.repaintClock)

		self.DecodedExtraFields = []
		for f in self.ExtraFields:
			if ':' in f:
				self.DecodedExtraFields.append(f.split(':'))
			else:
				logsupport.Logs.Log("Incomplete field specified on clockscreen", severity=ConsoleWarning)

	def repaintClock(self):
		usefulheight = config.screenheight - config.topborder - config.botborder
		h = 0
		l = []

		for i in range(len(self.OutFormat)):
			l.append(
				config.fonts.Font(self.CharSize[i], self.Font).render(time.strftime(self.OutFormat[i]),
																	  0, wc(self.CharColor)))
			h = h + l[i].get_height()
		if self.ExtraSize[0] != 0:
			cb = CreateWeathBlock(self.ExtraFormat, self.DecodedExtraFields, self.Font,
							  self.ExtraSize, self.CharColor, None, True)
			h = h + cb.get_height()
		s = (usefulheight - h)/(len(l))

		config.screen.fill(wc(self.BackgroundColor),
						   pygame.Rect(0, 0, config.screenwidth, config.screenheight - config.botborder))
		vert_off = config.topborder
		for i in range(len(l)):
			horiz_off = (config.screenwidth - l[i].get_width())//2
			config.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		if self.ExtraSize[0] != 0:
			# noinspection PyUnboundLocalVariable
			horiz_off = (config.screenwidth - cb.get_width())//2
			config.screen.blit(cb, (horiz_off, vert_off))
		pygame.display.update()
		config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)

	def InitDisplay(self, nav):
		super(ClockScreenDesc, self).InitDisplay(nav)
		self.repaintClock()

config.screentypes["Clock"] = ClockScreenDesc
