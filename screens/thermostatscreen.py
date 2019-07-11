import functools

import pygame
import xmltodict
from pygame import gfxdraw

import debug
import fonts
import hw
import hubs.isy.isy as isy  # only to test that the hub for this is an ISY hub
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from hw import scaleW, scaleH
from logsupport import ConsoleWarning, ConsoleError
from utilfuncs import wc


def trifromtop(h, v, n, size, c, invert):
	if invert:
		return h * n, v + size // 2, h * n - size // 2, v - size // 2, h * n + size // 2, v - size // 2, c
	else:
		return h * n, v - size // 2, h * n - size // 2, v + size // 2, h * n + size // 2, v + size // 2, c


class ThermostatScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "New ThermostatScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		screen.IncorporateParams(self, 'ThermostatScreen', {'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor'},
								 screensection)
		self.info = {}
		self.oldinfo = {}
		nominalfontsz = (30, 50, 80, 160)
		nominalspacers = (5, 20, 25, 40, 50, 85)

		self.fsize = []
		self.spacer = []
		if isinstance(self.DefaultHubObj, isy.ISY):
			self.isy = self.DefaultHubObj
			self.ISYObj = self.isy.GetNode(screenname)[0]  # use ControlObj (0)
			if self.ISYObj is None:
				logsupport.Logs.Log("No Thermostat: " + screenname, severity=ConsoleWarning)
		else:
			logsupport.Logs.Log("Thermostat screen only works with ISY hub", severity=ConsoleError)
			self.ISYObj = None

		self.SetScreenTitle(screen.FlatenScreenLabel(self.label), nominalfontsz[1], self.CharColor)
		self.TempPos = self.startvertspace
		'''
		Size and positions based on vertical screen space less top/bottom borders less default title size of 50
		Compute other fonts sizes based on what is left after that given user ability to set actual title size
		'''
		tempsurf = fonts.fonts.Font(50).render('Temp', 0, wc(self.CharColor))  # todo should the 50 be scaled now?
		sizingratio = self.useablevertspace / (self.useablevertspace + tempsurf.get_height())

		for fs in nominalfontsz:
			self.fsize.append(int(fs * sizingratio))
		for fs in nominalspacers:
			self.spacer.append(int(fs * sizingratio))

		self.StatePos = self.TempPos + fonts.fonts.Font(self.fsize[3]).get_linesize() - scaleH(self.spacer[1])
		self.SPPos = self.StatePos + scaleH(self.spacer[2])
		self.AdjButSurf = pygame.Surface((hw.screenwidth, scaleH(self.spacer[3])))
		self.AdjButTops = self.SPPos + fonts.fonts.Font(self.fsize[2]).get_linesize() - scaleH(self.spacer[0])
		centerspacing = hw.screenwidth // 5
		self.SPHPosL = int(1.5 * centerspacing)
		self.SPHPosR = int(3.5 * centerspacing)
		self.AdjButSurf.fill(wc(self.BackgroundColor))
		arrowsize = scaleH(self.spacer[3])  # pixel

		for i in range(4):
			gfxdraw.filled_trigon(self.AdjButSurf, *trifromtop(centerspacing, arrowsize // 2, i + 1, arrowsize,
															   wc(("red", "blue", "red", "blue")[i]), i % 2 != 0))
			self.Keys['temp' + str(i)] = toucharea.TouchPoint('temp' + str(i),
															  (centerspacing * (i + 1),
															   self.AdjButTops + arrowsize // 2),
															  (arrowsize * 1.2, arrowsize * 1.2),
															  proc=functools.partial(self.BumpTemp,
																					 ('CLISPH', 'CLISPH', 'CLISPC',
																					  'CLISPC')[i],
																					 (2, -2, 2, -2)[i]))

		self.ModeButPos = self.AdjButTops + scaleH(self.spacer[5])  # pixel

		bsize = (scaleW(100), scaleH(self.spacer[4]))  # pixel

		self.Keys['Mode'] = toucharea.ManualKeyDesc(self, "Mode", ["Mode"],
													self.KeyColor, self.CharColor, self.CharColor,
													center=(self.SPHPosL, self.ModeButPos), size=bsize,
													KOn=self.KeyOffOutlineColor,
													proc=functools.partial(self.BumpMode, 'CLIMD', range(8)))

		self.Keys['Fan'] = toucharea.ManualKeyDesc(self, "Fan", ["Fan"],
												   self.KeyColor, self.CharColor, self.CharColor,
												   center=(self.SPHPosR, self.ModeButPos), size=bsize,
												   KOn=self.KeyOffOutlineColor,
												   proc=functools.partial(self.BumpMode, 'CLIFS', (7, 8)))

		self.ModesPos = self.ModeButPos + bsize[1] // 2 + scaleH(self.spacer[0])
		if self.ISYObj is not None:
			self.HubInterestList[self.isy.name] = {
				self.ISYObj.address: self.Keys['Mode']}  # placeholder for thermostat node
		utilities.register_example("ThermostatScreenDesc", self)

	# noinspection PyUnusedLocal
	def BumpTemp(self, setpoint, degrees):
		debug.debugPrint('Main', "Bump temp: ", setpoint, degrees, ' to ', self.info[setpoint][0] + degrees)
		self.isy.try_ISY_comm('nodes/' + self.ISYObj.address + '/cmd/' + setpoint + '/' + str(
			self.info[setpoint][0] + degrees))  # todo fix for lost connect when move to common screen

	# noinspection PyUnusedLocal
	def BumpMode(self, mode, vals):
		cv = vals.index(self.info[mode][0])
		cv = (cv + 1) % len(vals)
		debug.debugPrint('Main', "Bump: ", mode, ' to ', cv)
		self.isy.try_ISY_comm('nodes/' + self.ISYObj.address + '/cmd/' + mode + '/' + str(
			vals[cv]))  # todo fix for lost connect when move to common screen

	def ShowScreen(self):
		print(self.ISYObj.GetThermInfo())
		rtxt = self.isy.try_ISY_comm(
			'nodes/' + self.ISYObj.address)  # todo fix for lost connect when move to common screen
		# noinspection PyBroadException
		try:
			tstatdict = xmltodict.parse(rtxt)
		except:
			logsupport.Logs.Log("Thermostat node sent garbage: ", rtxt, severity=ConsoleWarning)
			return
		props = tstatdict["nodeInfo"]["properties"]["property"]
		self.oldinfo = dict(self.info)
		self.info = {}
		dbgStr = ''
		for item in props:
			dbgStr = dbgStr + item["@id"] + ':' + item["@formatted"] + "(" + item["@value"] + ")  "
			#			debug.debugPrint('Main', item["@id"]+":("+item["@value"]+"):"+item["@formatted"])
			# noinspection PyBroadException
			try:
				self.info[item["@id"]] = (int(item['@value']), item['@formatted'])
			except:
				self.info[item["@id"]] = (0, item['@formatted'])
		debug.debugPrint('Main', dbgStr)
		if self.oldinfo == {}:
			self.oldinfo = dict(self.info)  # handle initial case
			updtneeded = True
		else:
			updtneeded = False
		for i, val in self.info.items():
			if self.oldinfo[i] != val:
				updtneeded = True
				debug.debugPrint('Main', 'Tstat reading change: ', i + ':', self.oldinfo[i], '->', self.info[i])

		if not updtneeded:
			return
		self.ReInitDisplay()
		r = fonts.fonts.Font(self.fsize[3], bold=True).render(u"{:4.1f}".format(self.info["ST"][0] // 2), 0,
															  wc(self.CharColor))
		hw.screen.blit(r, ((hw.screenwidth - r.get_width()) // 2, self.TempPos))
		if isinstance(self.info["CLIHCS"][0], int):
			r = fonts.fonts.Font(self.fsize[0]).render(("Idle", "Heating", "Cooling")[self.info["CLIHCS"][0]], 0,
													   wc(self.CharColor))
		else:
			r = fonts.fonts.Font(self.fsize[0]).render("n/a", 0, wc(self.CharColor))
		hw.screen.blit(r, ((hw.screenwidth - r.get_width()) // 2, self.StatePos))
		# r = config.fonts.Font(self.fsize[2]).render(
		#	"{:2d}    {:2d}".format(self.info["CLISPH"][0]//2, self.info["CLISPC"][0]//2), 0,
		#	wc(self.CharColor))
		rL = fonts.fonts.Font(self.fsize[2]).render(
			"{:2d}".format(self.info["CLISPH"][0] // 2), 0, wc(self.CharColor))
		rH = fonts.fonts.Font(self.fsize[2]).render(
			"{:2d}".format(self.info["CLISPC"][0] // 2), 0, wc(self.CharColor))
		hw.screen.blit(rL, (self.SPHPosL - rL.get_width() // 2, self.SPPos))
		hw.screen.blit(rH, (self.SPHPosR - rH.get_width() // 2, self.SPPos))
		hw.screen.blit(self.AdjButSurf, (0, self.AdjButTops))
		# noinspection PyBroadException
		try:
			r1 = fonts.fonts.Font(self.fsize[1]).render(
				('Off', 'Heat', 'Cool', 'Auto', 'Fan', 'Prog Auto', 'Prog Heat', 'Prog Cool')[self.info["CLIMD"][0]], 0,
				wc(self.CharColor))
		except:
			r1 = fonts.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		# noinspection PyBroadException
		try:
			r2 = fonts.fonts.Font(self.fsize[1]).render(('On', 'Auto')[self.info["CLIFS"][0] - 7], 0,
														wc(self.CharColor))
		except:
			r2 = fonts.fonts.Font(self.fsize[1]).render('---', 0, wc(self.CharColor))
		hw.screen.blit(r1, (self.Keys['Mode'].Center[0] - r1.get_width() // 2, self.ModesPos))
		hw.screen.blit(r2, (self.Keys['Fan'].Center[0] - r2.get_width() // 2, self.ModesPos))

		pygame.display.update()

	def InitDisplay(self, nav):
		super(ThermostatScreenDesc, self).InitDisplay(nav)
		self.info = {}  # clear any old info to force a display
		self.ShowScreen()

	def NodeEvent(self, hub='', node=0, value=0, varinfo=()):
		self.ShowScreen()


screens.screentypes["ThermostatOld"] = ThermostatScreenDesc
