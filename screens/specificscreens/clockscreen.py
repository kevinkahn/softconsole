import time

import debug
import logsupport
from screens import screen
import screens.__screens as screens
from utils import utilities, fonts, hw
from logsupport import ConsoleWarning
from utils.utilfuncs import wc
from utils.weatherfromatting import CreateWeathBlock


class ClockScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		super().__init__(screensection, screenname)
		debug.debugPrint('Screen', "Build Clock Screen")
		screen.AddUndefaultedParams(self, screensection, CharSize=[20], Font=fonts.monofont, OutFormat=[],
									ExtraFields=[],
									ExtraSize=[0], ExtraFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		self.KeyList = None  # no touch areas active on this screen
		utilities.register_example("ClockScreen", self)

		self.DecodedExtraFields = []
		for f in self.ExtraFields:
			if ':' in f:
				self.DecodedExtraFields.append(f.split(':'))
			else:
				logsupport.Logs.Log("Incomplete field specified on clockscreen", severity=ConsoleWarning)

	# noinspection PyUnusedLocal
	def ScreenContentRepaint(self):
		if not self.Active:
			return  # handle race conditions where repaint queued just before screen switch
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
		s = (self.useablevertspace - h) / (len(l))

		vert_off = self.startvertspace
		for i in range(len(l)):
			horiz_off = (hw.screenwidth - l[i].get_width()) // 2
			hw.screen.blit(l[i], (horiz_off, vert_off))
			vert_off = vert_off + s + l[i].get_height()
		if self.ExtraSize[0] != 0:
			horiz_off = (hw.screenwidth - cb.get_width()) // 2
			hw.screen.blit(cb, (horiz_off, vert_off))

	def InitDisplay(self, nav):
		super().InitDisplay(nav)

	def ReInitDisplay(self):
		super().ReInitDisplay()

screens.screentypes["Clock"] = ClockScreenDesc
