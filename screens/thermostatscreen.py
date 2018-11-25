import pygame
import logsupport
from logsupport import ConsoleWarning, ConsoleError
from pygame import gfxdraw
import isy # only to test that the hub for this is an ISY hub

import config
import debug
import screen
import xmltodict
import toucharea
import utilities
from utilities import scaleW, scaleH
from utilfuncs import wc
import functools


def trifromtop(h, v, n, size, c, invert):
	if invert:
		return h*n, v + size//2, h*n - size//2, v - size//2, h*n + size//2, v - size//2, c
	else:
		return h*n, v - size//2, h*n - size//2, v + size//2, h*n + size//2, v + size//2, c


class ThermostatScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "New ThermostatScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		screen.IncorporateParams(self, 'ThermostatScreen', {'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor'},
								 screensection)
		self.info = {}
		self.oldinfo = {}
		self.fsize = (30, 50, 80, 160)
		if isinstance(self.DefaultHubObj, isy.ISY):
			self.isy = self.DefaultHubObj
			self.ISYObj = self.isy.GetNode(screenname)[0]  # use ControlObj (0)
			if self.ISYObj is None:
				logsupport.Logs.Log("No Thermostat: " + screenname, severity=ConsoleWarning)
		else:
			logsupport.Logs.Log("Thermostat screen only works with ISY hub", severity=ConsoleError)
			self.ISYObj = None

		self.TitleRen = config.fonts.Font(self.fsize[1]).render(screen.FlatenScreenLabel(self.label), 0,
																wc(self.CharColor))
		self.TitlePos = ((config.screenwidth - self.TitleRen.get_width())//2, config.topborder)
		self.TempPos = config.topborder + self.TitleRen.get_height()
		self.StatePos = self.TempPos + config.fonts.Font(self.fsize[3]).get_linesize() - scaleH(20)
		self.SPPos = self.StatePos + scaleH(25)
		self.AdjButSurf = pygame.Surface((config.screenwidth, scaleH(40)))
		self.AdjButTops = self.SPPos + config.fonts.Font(self.fsize[2]).get_linesize() - scaleH(5)
		centerspacing = config.screenwidth//5
		self.SPHPosL = int(1.5 * centerspacing)
		self.SPHPosR = int(3.5 * centerspacing)
		self.AdjButSurf.fill(wc(self.BackgroundColor))
		arrowsize = scaleH(40)  # pixel

		for i in range(4):
			gfxdraw.filled_trigon(self.AdjButSurf, *trifromtop(centerspacing, arrowsize//2, i + 1, arrowsize,
															   wc(("red", "blue", "red", "blue")[i]), i%2 != 0))
			self.Keys['temp' + str(i)] = toucharea.TouchPoint('temp' + str(i),
															  (centerspacing*(i + 1), self.AdjButTops + arrowsize//2),
															  (arrowsize*1.2, arrowsize*1.2),
															  proc=functools.partial(self.BumpTemp,
																					 ('CLISPH', 'CLISPH', 'CLISPC', 'CLISPC')[i],
																					 (2, -2, 2, -2)[i]))

		self.ModeButPos = self.AdjButTops + scaleH(85)  # pixel

		bsize = (scaleW(100), scaleH(50))  # pixel

		self.Keys['Mode'] = toucharea.ManualKeyDesc(self, "Mode", ["Mode"],
													self.KeyColor, self.CharColor, self.CharColor,
													center=(config.screenwidth//4, self.ModeButPos), size=bsize,
													KOn=config.KeyOffOutlineColor,
													proc=functools.partial(self.BumpMode, 'CLIMD', range(8)))

		self.Keys['Fan'] = toucharea.ManualKeyDesc(self, "Fan", ["Fan"],
												   self.KeyColor, self.CharColor, self.CharColor,
												   center=(3*config.screenwidth//4, self.ModeButPos), size=bsize,
												   KOn=config.KeyOffOutlineColor,
												   proc=functools.partial(self.BumpMode, 'CLIFS', (7, 8)))

		self.ModesPos = self.ModeButPos + bsize[1]//2 + scaleH(5)
		if self.ISYObj is not None:
			self.HubInterestList[self.isy.name] = {self.ISYObj.address: self.Keys['Mode']} # placeholder for thermostat node
		utilities.register_example("ThermostatScreenDesc", self)

	# noinspection PyUnusedLocal
	def BumpTemp(self, setpoint, degrees, presstype):
		debug.debugPrint('Main', "Bump temp: ", setpoint, degrees,' to ',self.info[setpoint][0] + degrees)
		self.isy.try_ISY_comm('nodes/' + self.ISYObj.address + '/cmd/' + setpoint + '/' + str(
				self.info[setpoint][0] + degrees))  # todo fix for lost connect when move to common screen

	# noinspection PyUnusedLocal
	def BumpMode(self, mode, vals, presstype):
		cv = vals.index(self.info[mode][0])
		cv = (cv + 1)%len(vals)
		debug.debugPrint('Main', "Bump: ", mode, ' to ', cv)
		self.isy.try_ISY_comm('nodes/' + self.ISYObj.address + '/cmd/' + mode + '/' + str(vals[cv])) # todo fix for lost connect when move to common screen

	def ShowScreen(self):
		rtxt = self.isy.try_ISY_comm('nodes/' + self.ISYObj.address) # todo fix for lost connect when move to common screen
		# noinspection PyBroadException
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
			# noinspection PyBroadException
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
		for i,val in self.info.items():
			if self.oldinfo[i] != val:
				updtneeded = True
				debug.debugPrint('Main','Tstat reading change: ',i+':',self.oldinfo[i],'->',self.info[i])

		if not updtneeded:
			return
		self.ReInitDisplay()
		config.screen.blit(self.TitleRen, self.TitlePos)
		r = config.fonts.Font(self.fsize[3], bold=True).render(u"{:4.1f}".format(self.info["ST"][0]//2), 0,
															   wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())//2, self.TempPos))
		if isinstance(self.info["CLIHCS"][0], int):
			r = config.fonts.Font(self.fsize[0]).render(("Idle", "Heating", "Cooling")[self.info["CLIHCS"][0]], 0,
													wc(self.CharColor))
		else:
			r = config.fonts.Font(self.fsize[0]).render("n/a", 0, wc(self.CharColor))
		config.screen.blit(r, ((config.screenwidth - r.get_width())//2, self.StatePos))
		# r = config.fonts.Font(self.fsize[2]).render(
		#	"{:2d}    {:2d}".format(self.info["CLISPH"][0]//2, self.info["CLISPC"][0]//2), 0,
		#	wc(self.CharColor))
		rL = config.fonts.Font(self.fsize[2]).render(
			"{:2d}".format(self.info["CLISPH"][0] // 2), 0, wc(self.CharColor))
		rH = config.fonts.Font(self.fsize[2]).render(
			"{:2d}".format(self.info["CLISPC"][0] // 2), 0, wc(self.CharColor))
		config.screen.blit(rL, (self.SPHPosL - rL.get_width() // 2, self.SPPos))
		config.screen.blit(rH, (self.SPHPosR - rH.get_width() // 2, self.SPPos))
		config.screen.blit(self.AdjButSurf, (0, self.AdjButTops))
		# noinspection PyBroadException
		try:
			r1 = config.fonts.Font(self.fsize[1]).render(
				('Off', 'Heat', 'Cool', 'Auto', 'Fan', 'Prog Auto', 'Prog Heat', 'Prog Cool')[self.info["CLIMD"][0]], 0,
				wc(self.CharColor))
		except:
			r1 = config.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		# noinspection PyBroadException
		try:
			r2 = config.fonts.Font(self.fsize[1]).render(('On', 'Auto')[self.info["CLIFS"][0] - 7], 0,
														 wc(self.CharColor))
		except:
			r2 = config.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		config.screen.blit(r1, (self.Keys['Mode'].Center[0] - r1.get_width()//2, self.ModesPos))
		config.screen.blit(r2, (self.Keys['Fan'].Center[0] - r2.get_width()//2, self.ModesPos))

		pygame.display.update()

	def InitDisplay(self, nav):
		super(ThermostatScreenDesc, self).InitDisplay(nav)
		self.info = {} # clear any old info to force a display
		self.ShowScreen()

	def NodeEvent(self, hub ='', node=0, value=0, varinfo = ()):
		self.ShowScreen()

config.screentypes["Thermostat"] = ThermostatScreenDesc
