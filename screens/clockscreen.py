import fonts
import hw
import screens.__screens as screens
from utilfuncs import wc
import config
import time
import pygame
import debug
import screen
import utilities
#from eventlist import ProcEventItem
import logsupport
from logsupport import ConsoleWarning
from weatherfromatting import CreateWeathBlock
from timers import RepeatingPost


class ClockScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		screen.ScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "Build Clock Screen")
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=fonts.monofont, OutFormat=[],
									ExtraFields=[],
									ExtraSize=[0], ExtraFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.KeyList = None  # no touch areas active on this screen
		utilities.register_example("ClockScreen", self)
		#self.ClockRepaintEvent = ProcEventItem(id(self), 'clockrepaint', self.repaintClock)

		self.DecodedExtraFields = []
		for f in self.ExtraFields:
			if ':' in f:
				self.DecodedExtraFields.append(f.split(':'))
			else:
				logsupport.Logs.Log("Incomplete field specified on clockscreen", severity=ConsoleWarning)
		self.poster = RepeatingPost(1,paused=True, name=self.name,proc=self.repaintClock)
		self.poster.start()

	def repaintClock(self):
		h = 0
		l = []

		for i in range(len(self.OutFormat)):
			l.append(
				fonts.fonts.Font(self.CharSize[i], self.Font).render(time.strftime(self.OutFormat[i]),
																	 0, wc(self.CharColor)))
			h = h + l[i].get_height()
		if self.ExtraSize[0] != 0:
			cb = CreateWeathBlock(self.ExtraFormat, self.DecodedExtraFields, self.Font,
								  self.ExtraSize, self.CharColor, None, True, useicon=False)
			h = h + cb.get_height()
		s = (self.useablevertspace - h)/(len(l))

		self.ReInitDisplay()
		vert_off = self.startvertspace
		for i in range(len(l)):
			horiz_off = (hw.screenwidth - l[i].get_width()) // 2
			config.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		if self.ExtraSize[0] != 0:
			# noinspection PyUnboundLocalVariable
			horiz_off = (hw.screenwidth - cb.get_width()) // 2
			config.screen.blit(cb, (horiz_off, vert_off))
		pygame.display.update()
		#config.DS.Tasks.AddTask(self.ClockRepaintEvent, 1)
		self.poster.resume()

	def InitDisplay(self, nav):
		super(ClockScreenDesc, self).InitDisplay(nav)
		self.repaintClock()

	def ExitScreen(self):
		self.poster.pause()
		screen.ScreenDesc.ExitScreen(self)


screens.screentypes["Clock"] = ClockScreenDesc
