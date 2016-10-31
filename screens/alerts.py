import webcolors

wc = webcolors.name_to_rgb
import config
import time
import pygame
from config import debugPrint, WAITEXIT
import screen
import utilities


class AlertsScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('BuildScreen', "Build Alerts Screen")
		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, CharSize=[20], Font='droidsansmono', OutFormat=[])
		for i in range(len(self.CharSize), len(self.OutFormat)):
			self.CharSize.append(self.CharSize[-1])
		utilities.register_example("AlertsScreen", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     ClockScreenDesc:" + str(self.CharColor) + ":" + str(
			self.OutFormat) + ":" + str(self.CharSize)

	def HandleScreen(self, newscr=True):
		pass


config.screentypes["Alert"] = AlertsScreenDesc
