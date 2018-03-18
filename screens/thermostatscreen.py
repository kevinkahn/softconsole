import pygame
import logsupport
from logsupport import ConsoleWarning
from pygame import gfxdraw

import config
import isy
import debug
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
		debug.debugPrint('Screen', "New ThermostatScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor')
		self.info = {}
		self.fsize = (30, 50, 80, 160)

		if config.ISY.NodeExists(screenname):
			self.ISYObj = config.ISY.GetNodeByName(screenname)
		else:
			self.ISYObj = None
			logsupport.Logs.Log("No Thermostat: " + screenname, severity=ConsoleWarning)

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

		self.ModesPos = self.ModeButPos + bsize[1]/2 + scaleH(5)
		if self.ISYObj != None:
			self.NodeList[self.ISYObj.address] = self.Keys['Mode']  # placeholder for thermostat node
		utilities.register_example("ThermostatScreenDesc", self)

	def BumpTemp(self, setpoint, degrees, presstype):

		debug.debugPrint('Main', "Bump temp: ", setpoint, degrees,' to ',self.info[setpoint][0] + degrees)
		rtxt = isy.try_ISY_comm('/rest/nodes/' + self.ISYObj.address + '/cmd/' + setpoint + '/' + str(
				self.info[setpoint][0] + degrees))

	def BumpMode(self, mode, vals, presstype):

		cv = vals.index(self.info[mode][0])
		cv = (cv + 1)%len(vals)
		debug.debugPrint('Main', "Bump: ", mode, ' to ', cv)
		rtxt = isy.try_ISY_comm('/rest/nodes/' + self.ISYObj.address + '/cmd/' + mode + '/' + str(vals[cv]))

	def ShowScreen(self):
		rtxt = isy.try_ISY_comm('/rest/nodes/' + self.ISYObj.address)
		try:
			tstatdict = xmltodict.parse(rtxt)
		except:
			logsupport.Logs.Log("Thermostat node sent garbage: ",rtxt,severity=ConsoleWarning)
			return
		props = tstatdict["nodeInfo"]["properties"]["property"]
		self.oldinfo = dict(self.info)
		self.info = {}
		dbgStr = ''
		for item in props:
			dbgStr = dbgStr + item["@id"]+':'+item["@formatted"]+"("+item["@value"]+")  "
#			debug.debugPrint('Main', item["@id"]+":("+item["@value"]+"):"+item["@formatted"])
			try:
				self.info[item["@id"]] = (int(item['@value']), item['@formatted'])
			except:
				self.info[item["@id"]] = (0, item['@formatted'])
		debug.debugPrint('Main',dbgStr)
		if self.oldinfo == {}:
			self.oldinfo = dict(self.info) # handle initial case
			updtneeded = True
		else:
			updtneeded = False
		for i,val in self.info.iteritems():
			if self.oldinfo[i] != val:
				updtneeded = True
				debug.debugPrint('Main','Tstat reading change: ',i+':',self.oldinfo[i],'->',self.info[i])
		config.screen.blit(self.TitleRen, self.TitlePos)
		if not updtneeded:
			return
		self.ReInitDisplay()
		r = config.fonts.Font(self.fsize[3], bold=True).render(u"{:4.1f}".format(self.info["ST"][0]/2), 0,
															   wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())/2, self.TempPos))
		if isinstance(self.info["CLIHCS"][0], int):
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
		try:
			r1 = config.fonts.Font(self.fsize[1]).render(
				('Off', 'Heat', 'Cool', 'Auto', 'Fan', 'Prog Auto', 'Prog Heat', 'Prog Cool')[self.info["CLIMD"][0]], 0,
				wc(self.CharColor))
		except:
			r1 = config.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		try:
			r2 = config.fonts.Font(self.fsize[1]).render(('On', 'Auto')[self.info["CLIFS"][0] - 7], 0,
														 wc(self.CharColor))
		except:
			r2 = config.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		config.screen.blit(r1, (self.Keys['Mode'].Center[0] - r1.get_width()/2, self.ModesPos))
		config.screen.blit(r2, (self.Keys['Fan'].Center[0] - r2.get_width()/2, self.ModesPos))

		pygame.display.update()

	def InitDisplay(self, nav):
		super(ThermostatScreenDesc, self).InitDisplay(
			nav)  # todo what actually gets returned for thermo?  needed if want to optimize showscreen
		self.info = {} # clear any old info to force a display
		self.ShowScreen()

	def ISYEvent(self, node, value):
		self.ShowScreen()

config.screentypes["Thermostat"] = ThermostatScreenDesc
