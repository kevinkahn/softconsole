import functools
import time

import pygame

import config
import debug
import fonts
import hw
import logsupport
import screen
import toucharea
import utilities
from utilfuncs import wc, interval_str

fixedoverrides = {'CharColor': 'white', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'], 'DimTO': 60,
				  'PersistTO': 5}


class MaintScreenDesc(screen.BaseKeyScreenDesc):
	# noinspection PyDefaultArgument
	def __init__(self, name, keys, overrides=fixedoverrides):
		screen.BaseKeyScreenDesc.__init__(self, overrides, name)
		debug.debugPrint('Screen', "Build Maintenance Screen")
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		for k, kt in keys.items():
			NK = toucharea.ManualKeyDesc(self, k, [kt[0]], 'gold', 'black', 'red', KOn='black', KOff='red')
			if kt[1] is not None:
				if len(kt) == 3:  # need to add key reference to the proc for this key
					NK.Proc = functools.partial(kt[1], NK)
				else:
					NK.Proc = kt[1]
			self.Keys[k] = NK
		topoff = self.TitleFontSize + self.SubFontSize
		self.LayoutKeys(topoff, self.useablevertspacesansnav - topoff)
		self.DimTO = 60
		self.PersistTO = 1  # setting to 0 would turn off timer and stick us here
		utilities.register_example("MaintScreenDesc", self)

	def ShowScreen(self):
		self.ReInitDisplay()
		# self.PaintBase()
		r = fonts.fonts.Font(self.TitleFontSize, '', True, True).render("Console Maintenance", 0, wc(self.CharColor))
		rl = (hw.screenwidth - r.get_width()) / 2
		hw.screen.blit(r, (rl, self.TopBorder))
		r = fonts.fonts.Font(self.SubFontSize, '', True, True).render(
			"Up: " + interval_str(time.time() - config.sysStore.ConsoleStartTime),
			0, wc(self.CharColor))
		rl = (hw.screenwidth - r.get_width()) / 2
		hw.screen.blit(r, (rl, self.TopBorder + self.TitleFontSize))
		self.PaintKeys()
		pygame.display.update()

	def InitDisplay(self, nav):
		debug.debugPrint('Main', "Enter to screen: ", self.name)
		logsupport.Logs.Log('Entering Maintenance Screen: ' + self.name)
		super(MaintScreenDesc, self).InitDisplay(nav)
		self.ShowScreen()
