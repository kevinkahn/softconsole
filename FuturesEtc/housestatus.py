import config
import pygame
import debug
import screen
import utilities
import pygame

import config
import debug
import screen
import utilities


class HouseStatusScreenDesc(screen.ScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "Build House Status Screen")
		screen.ScreenDesc.__init__(self, screensection, screenname)  # no extra cmd keys
		utilities.LocalizeParams(self, screensection, '-', NormalOn=[], NormalOff=[])
		checklist = [nm for nm in config.ISY.NodesByName if
					 ((nm in self.NormalOn) or (nm in self.NormalOff))]  # addr -> name
		utilities.register_example("HouseStatusScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     StatusScreenDesc:"

	def SetUp(self):
		pass

	def HandleScreen(self, newscr=True):

		# stop any watching for device stream
		config.toDaemon.put([])
		print(self.NormalOn)
		print(self.NormalOff)
		checknodes = [nm for nm in config.ISY.NodesByName if ((nm in self.NormalOn) or (nm in self.NormalOff))]
		print(checknodes)
		# states = isy.get_real_time_status([config.ISY.NodesByName[x].address for x in checknodes])
		print(states)
		outspecnodes = []
		for node in states:
			nodename = config.ISY.NodesByAddr[node]
			if ((nodename in self.NormalOn) and (states[node] == 0)) or (
						(nodename in self.NormalOff) and (states[node] != 0)):
				outspecnodes.append(node)
		for node in outspecnodes:
			print(node, config.ISY.NodesByAddr[node].name, states[node])

		self.PaintBase()

		pygame.display.update()

		while 1:
			choice = config.DS.NewWaitPress(self)
			if choice[0] == 0:
				return choice[1]


config.screentypes["Status"] = HouseStatusScreenDesc
