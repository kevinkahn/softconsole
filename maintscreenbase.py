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
import supportscreens
from utilfuncs import wc, interval_str
import configobj

fixedoverrides = {'CharColor': 'white', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'], 'DimTO': 60,
				  'PersistTO': 5, 'KeyColorOff': 'green'}


class MaintScreenDesc(screen.BaseKeyScreenDesc):
	# noinspection PyDefaultArgument
	def __init__(self, name, keys, overrides=None, Clocked=0):
		# the following works around what looks like a bug - if I just set overrides=fixoverrides above it keeps using last call's overrides
		global fixedoverrides
		ov = configobj.ConfigObj(overrides) if overrides is not None else configobj.ConfigObj(fixedoverrides)
		super().__init__(ov, name, Clocked=Clocked)
		debug.debugPrint('Screen', "Build Maintenance Screen")
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.SetScreenTitle(name, self.TitleFontSize, 'white')
		for k, kt in keys.items():
			verify = False if len(kt) < 4 else kt[3] == 'True'
			DblTap = None if len(kt) < 3 else kt[2]
			DN = [kt[0]] if isinstance(kt[0], str) else kt[0]
			self.Keys[k] = toucharea.ManualKeyDesc(self, k, DN, 'gold', 'black', 'red', KOn='black', KOff='red',
												   Verify=verify, proc=kt[1], procdbl=DblTap)
			if verify:
				VerifyScreen = supportscreens.VerifyScreen(self.Keys[k], ('Proceed',), ('Cancel',), kt[1],
														   self, self.Keys[k].KeyColorOff, self.Keys[k].BackgroundColor,
														   self.Keys[k].CharColor,
														   True, self.HubInterestList)
				self.Keys[k].InsertVerify(VerifyScreen)

		topoff = self.SubFontSize
		self.LayoutKeys(topoff, self.useablevertspacesansnav - topoff)
		self.DimTO = 60
		self.PersistTO = 1  # setting to 0 would turn off timer and stick us here
		utilities.register_example("MaintScreenDesc", self)

	def ShowScreen(self):
		# todo use screentitle stuff
		self.ReInitDisplay()
		# r = fonts.fonts.Font(self.TitleFontSize, '', True, True).render("Console Maintenance", 0, wc(self.CharColor))
		# rl = (hw.screenwidth - r.get_width()) / 2
		#hw.screen.blit(r, (rl, self.TopBorder))
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
