import pygame
import logsupport
from pygame import gfxdraw

import config
from debug import debugPrint
import screen
import xmltodict
import toucharea
import utilities
from utilities import scaleW, scaleH, wc
import functools


def trifromtop(h, v, n, size, c, invert):
	if invert:
		return h*n, v + size/2, h*n - size/2, v - size/2, h*n + size/2, v - size/2, c
	else:
		return h*n, v - size/2, h*n - size/2, v + size/2, h*n + size/2, v + size/2, c


class ThermostatScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New ThermostatScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor')
		self.info = {}
		self.fsize = (30, 50, 80, 160)

		if screenname in config.ISY.NodesByName:
			self.ISYObj = config.ISY.NodesByName[screenname]
		else:
			self.ISYObj = None
			config.Logs.Log("No Thermostat: " + screenname, severity=logsupport.ConsoleWarning)

		self.TitleRen = config.fonts.Font(self.fsize[1]).render(screen.FlatenScreenLabel(self.label), 0,
																wc(self.CharColor))
		self.TitlePos = ((config.screenwidth - self.TitleRen.get_width())/2, config.topborder)
		self.TempPos = config.topborder + self.TitleRen.get_height()
		self.StatePos = self.TempPos + config.fonts.Font(self.fsize[3]).get_linesize() - scaleH(20)
		self.SPPos = self.StatePos + scaleH(25)
		self.AdjButSurf = pygame.Surface((config.screenwidth, scaleH(40)))
		self.AdjButTops = self.SPPos + config.fonts.Font(self.fsize[2]).get_linesize() - scaleH(5)
		centerspacing = config.screenwidth/5
		self.AdjButSurf.fill(wc(self.BackgroundColor))
		arrowsize = scaleH(40)  # pixel

		for i in range(4):
			gfxdraw.filled_trigon(self.AdjButSurf, *trifromtop(centerspacing, arrowsize/2, i + 1, arrowsize,
															   wc(("red", "blue", "red", "blue")[i]), i%2 <> 0))
			self.Keys['temp' + str(i)] = toucharea.TouchPoint('temp' + str(i),
															  (centerspacing*(i + 1), self.AdjButTops + arrowsize/2),
															  (arrowsize*1.2, arrowsize*1.2),
															  proc=functools.partial(self.BumpTemp,
																					 ('CLISPH', 'CLISPH', 'CLISPC', 'CLISPC')[i],
																					 (2, -2, 2, -2)[i]))

		self.ModeButPos = self.AdjButTops + scaleH(85)  # pixel

		bsize = (scaleW(100), scaleH(50))  # pixel

		self.Keys['Mode'] = toucharea.ManualKeyDesc(self, "Mode", ["Mode"],
													self.KeyColor, self.CharColor, self.CharColor,
													center=(config.screenwidth/4, self.ModeButPos), size=bsize,
													KOn=config.KeyOffOutlineColor,
													proc=functools.partial(self.BumpMode, 'CLIMD', range(8)))

		self.Keys['Fan'] = toucharea.ManualKeyDesc(self, "Fan", ["Fan"],
												   self.KeyColor, self.CharColor, self.CharColor,
												   center=(3*config.screenwidth/4, self.ModeButPos), size=bsize,
												   KOn=config.KeyOffOutlineColor,
												   proc=functools.partial(self.BumpMode, 'CLIFS', (7, 8)))
		self.Keys['Mode'].FinishKey((0, 0), (0, 0))
		self.Keys['Fan'].FinishKey((0, 0), (0, 0))
		self.ModesPos = self.ModeButPos + bsize[1]/2 + scaleH(5)
		utilities.register_example("ThermostatScreenDesc", self)

	def BumpTemp(self, setpoint, degrees, presstype):

		debugPrint('Main', "Bump temp: ", setpoint, degrees)
		debugPrint('Main', "New: ", self.info[setpoint][0] + degrees)
		r = config.ISYrequestsession.get(
			config.ISYprefix + 'nodes/' + self.ISYObj.address + '/set/' + setpoint + '/' + str(
				self.info[setpoint][0] + degrees))
		self.ShowScreen()

	def BumpMode(self, mode, vals, presstype):
		debugPrint('Main', "Bump mode: ", mode, vals)
		cv = vals.index(self.info[mode][0])
		debugPrint('Main', cv, vals[cv])
		cv = (cv + 1)%len(vals)
		debugPrint('Main', "new cv: ", cv)
		r = config.ISYrequestsession.get(
			config.ISYprefix + 'nodes/' + self.ISYObj.address + '/set/' + mode + '/' + str(vals[cv]))
		self.ShowScreen()

	def ShowScreen(self):
		self.ReInitDisplay()
		r = config.ISYrequestsession.get('http://' + config.ISYaddr + '/rest/nodes/' + self.ISYObj.address,
										 verify=False)  # todo check r response
		tstatdict = xmltodict.parse(r.text)
		props = tstatdict["nodeInfo"]["properties"]["property"]

		self.info = {}
		for item in props:
			debugPrint('Main', item["@id"], ":", item["@value"], ":", item["@formatted"])
			try:
				self.info[item["@id"]] = (int(item['@value']), item['@formatted'])
			except:
				self.info[item["@id"]] = (0, item['@formatted'])
		config.screen.blit(self.TitleRen, self.TitlePos)
		r = config.fonts.Font(self.fsize[3], bold=True).render(u"{:4.1f}".format(self.info["ST"][0]/2), 0,
															   wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())/2, self.TempPos))
		if isinstance(self.info["CLIHCS"][0], int):  # todo now redundant given I force to 0 above
			r = config.fonts.Font(self.fsize[0]).render(("Idle", "Heating", "Cooling")[self.info["CLIHCS"][0]], 0,
													wc(self.CharColor))
		else:
			r = config.fonts.Font(self.fsize[0]).render("n/a", 0, wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())/2, self.StatePos))
		r = config.fonts.Font(self.fsize[2]).render(
			"{:2d}    {:2d}".format(self.info["CLISPH"][0]/2, self.info["CLISPC"][0]/2), 0,
			wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())/2, self.SPPos))
		config.screen.blit(self.AdjButSurf, (0, self.AdjButTops))
		# self.Keys['Mode'].PaintKey() # todo also painting in reinit and in init - should sort out
		#self.Keys['Fan'].PaintKey()
		r1 = config.fonts.Font(self.fsize[1]).render(
			('Off', 'Heat', 'Cool', 'Auto', 'Fan', 'Prog Auto', 'Prog Heat', 'Prog Cool')[self.info["CLIMD"][0]], 0,
			wc(self.CharColor))
		r2 = config.fonts.Font(self.fsize[1]).render(('On', 'Auto')[self.info["CLIFS"][0] - 7], 0, wc(self.CharColor))
		config.screen.blit(r1, (self.Keys['Mode'].Center[0] - r1.get_width()/2, self.ModesPos))
		config.screen.blit(r2, (self.Keys['Fan'].Center[0] - r2.get_width()/2, self.ModesPos))

		pygame.display.update()

	def EnterScreen(self):
		debugPrint('Main', "Enter to screen: ", self.name)
		self.NodeWatch = [self.ISYObj.address]

	def InitDisplay(self, nav):
		super(ThermostatScreenDesc, self).InitDisplay(
			nav)  # todo what actually gets returned for thermo?  needed if want to optimize showscreen
		self.ShowScreen()

	def ISYEvent(self, node, value):
		self.ShowScreen()

config.screentypes["Thermostat"] = ThermostatScreenDesc
