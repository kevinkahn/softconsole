import functools

import pygame
from pygame import gfxdraw

import config
import debug
import fonts
import hw
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from hw import scaleW, scaleH
from logsupport import ConsoleWarning
from utilfuncs import wc


def trifromtop(h, v, n, size, c, invert):
	if invert:
		return h * n, v + size // 2, h * n - size // 2, v - size // 2, h * n + size // 2, v - size // 2, c
	else:
		return h * n, v - size // 2, h * n - size // 2, v + size // 2, h * n + size // 2, v + size // 2, c


class NestThermostatScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "New Nest ThermostatScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		screen.IncorporateParams(self, 'NestThermostatScreen', {'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor'},
								 screensection)
		nominalfontsz = (30, 50, 80, 160)
		nominalspacers = (5, 20, 25, 40, 50, 85)
		self.fsize = []
		self.spacer = []

		self.HA = self.DefaultHubObj
		self.ThermNode = self.HA.GetNode(screenname)[0]  # use ControlObj (0)
		if self.ThermNode is None:
			logsupport.Logs.Log("No Thermostat: " + screenname, severity=ConsoleWarning)
			raise ValueError
		# if isinstance(self.DefaultHub,hasshub.HA):
		#	self.HA = self.DefaultHub
		#	self.ThermNode = self.HA.GetNode(screenname)[0]  # use ControlObj (0)
		#	if self.ThermNode is None:
		#		logsupport.Logs.Log("No Thermostat: " + screenname, severity=ConsoleWarning)
		#		raise ValueError
		# else:
		#	logsupport.Logs.Log("Nest Thermostat screen only works with HA hub", severity=ConsoleError)
		#	self.self.ThermNode = None
		#	raise ValueError

		self.SetScreenTitle(screen.FlatenScreenLabel(self.label), nominalfontsz[1], self.CharColor)
		self.TempPos = self.startvertspace
		'''
		Size and positions based on nominal 480 vertical screen less top/bottom borders less default title size of 50
		Compute other fonts sizes based on what is left after that given user ability to set actual title size
		'''
		tempsurf = fonts.fonts.Font(50).render('Temp', 0, wc(self.CharColor))
		useable = self.useablevertspace / (self.initialvertspace - tempsurf.get_height())

		for fs in nominalfontsz:
			self.fsize.append(int(fs * useable))

		for fs in nominalspacers:
			self.spacer.append(int(fs * useable))

		self.StatePos = self.TempPos + fonts.fonts.Font(self.fsize[3]).get_linesize() - scaleH(self.spacer[1])
		self.SPVPos = self.StatePos + scaleH(self.spacer[2])
		sp = fonts.fonts.Font(self.fsize[2]).render("{:2d}".format(99), 0, wc(self.CharColor))
		self.SPHgt = sp.get_height()
		self.SPWdt = sp.get_width()
		self.SetPointSurf = pygame.Surface((self.SPWdt, self.SPHgt))
		self.SetPointSurf.fill(wc(self.BackgroundColor))
		self.AdjButSurf = pygame.Surface((hw.screenwidth, scaleH(self.spacer[3])))
		self.AdjButTops = self.SPVPos + fonts.fonts.Font(self.fsize[2]).get_linesize() - scaleH(self.spacer[0])
		centerspacing = hw.screenwidth // 5
		self.SPHPosL = int(1.5 * centerspacing)
		self.SPHPosR = int(3.5 * centerspacing)
		self.AdjButSurf.fill(wc(self.BackgroundColor))
		self.LocalOnly = [0.0, 0.0]  # Heat setpoint, Cool setpoint:  0 is normal color
		self.ModeLocal = 0.0
		self.FanLocal = 0.0
		arrowsize = scaleH(40)  # pixel todo should this be other than a constant?
		self.t_low = 0
		self.t_high = 99
		self.t_cur = 0
		self.t_state = "Unknown"
		self.mode = 'auto'
		self.fan = 'auto'
		self.modes, self.fanstates = self.ThermNode.GetModeInfo()
		self.TimeBumpSP = None
		self.TimeBumpModes = None
		self.TimeBumpFan = None
		self.TimerName = 0

		for i in range(4):
			gfxdraw.filled_trigon(self.AdjButSurf, *trifromtop(centerspacing, arrowsize // 2, i + 1, arrowsize,
															   wc(("red", "blue", "red", "blue")[i]), i % 2 != 0))
			self.Keys['temp' + str(i)] = toucharea.TouchPoint('temp' + str(i),
															  (centerspacing * (i + 1),
															   self.AdjButTops + arrowsize // 2),
															  (arrowsize * 1.2, arrowsize * 1.2),
															  proc=functools.partial(self.BumpTemp,
																					 (True, True, False, False)[i],
																					 (1, -1, 1, -1)[i]))

		self.ModeButPos = self.AdjButTops + scaleH(self.spacer[5])  # pixel

		bsize = (scaleW(100), scaleH(self.spacer[4]))  # pixel

		self.Keys['Mode'] = toucharea.ManualKeyDesc(self, "Mode", ["Mode"],
													self.KeyColor, self.CharColor, self.CharColor,
													center=(self.SPHPosL, self.ModeButPos), size=bsize,
													KOn=self.KeyOffOutlineColor,
													proc=self.BumpMode)

		self.Keys['Fan'] = toucharea.ManualKeyDesc(self, "Fan", ["Fan"],
												   self.KeyColor, self.CharColor, self.CharColor,
												   center=(self.SPHPosR, self.ModeButPos), size=bsize,
												   KOn=self.KeyOffOutlineColor,
												   proc=self.BumpFan)

		self.ModesPos = self.ModeButPos + bsize[1] // 2 + scaleH(self.spacer[0])
		if self.ThermNode is not None:
			self.HubInterestList[self.HA.name] = {
				self.ThermNode.address: self.Keys['Mode']}  # placeholder for thermostat node
		utilities.register_example("NestThermostatScreenDesc", self)

	# noinspection PyUnusedLocal
	def BumpTemp(self, heat, change, presstype):
		# heat: True if heat setpoint touched False for cool
		# change: 1 for up, -1 for down
		if self.TimeBumpSP is not None:
			self.TimeBumpSP.cancel()  # cancel any pending timer
		self.LocalOnly[not heat] = 0.50
		if heat:
			self.t_low += change
			hw.screen.blit(self.SetPointSurf, (self.SPHPosL - self.SPWdt // 2, self.SPVPos))
			rL = fonts.fonts.Font(self.fsize[2]).render("{:2d}".format(self.t_low), 0,
														wc(self.CharColor, factor=self.LocalOnly[0]))
			hw.screen.blit(rL, (self.SPHPosL - self.SPWdt // 2, self.SPVPos))
			pygame.display.update(pygame.Rect(self.SPHPosL - self.SPWdt // 2, self.SPVPos, self.SPWdt, self.SPHgt))
		else:
			self.t_high += change
			hw.screen.blit(self.SetPointSurf, (self.SPHPosR - self.SPWdt // 2, self.SPVPos))
			rH = fonts.fonts.Font(self.fsize[2]).render("{:2d}".format(self.t_high), 0,
														wc(self.CharColor, factor=self.LocalOnly[1]))
			hw.screen.blit(rH, (self.SPHPosR - self.SPWdt // 2, self.SPVPos))
			pygame.display.update(pygame.Rect(self.SPHPosR - self.SPWdt // 2, self.SPVPos, self.SPWdt, self.SPHgt))
		self.TimerName += 1
		self.TimeBumpSP = timers.OnceTimer(2.0, name='ThermostatSP' + str(self.TimerName), proc=self.PushTemp)
		self.TimeBumpSP.start()

	# push setpoint change after 2 seconds of idle

	# noinspection PyUnusedLocal
	def PushTemp(self, param):
		# called on callback timeout
		self.ThermNode.PushSetpoints(self.t_low, self.t_high)

	# noinspection PyUnusedLocal
	def PushModes(self, param):
		# called on callback timeout
		self.ThermNode.PushMode(self.mode)

	# noinspection PyUnusedLocal
	def PushFanState(self, param):
		self.ThermNode.PushFanState(self.fan)

	# noinspection PyUnusedLocal
	def BumpMode(self, presstype):
		if self.TimeBumpModes is not None:
			self.TimeBumpModes.cancel()  # cancel any pending timer
		self.ModeLocal = 0.5  # just do a show screen for mode and fan
		self.modes = self.modes[1:] + self.modes[:1]
		self.mode = self.modes[0]

		debug.debugPrint('Main', "Bump mode: ", self.mode)
		self.ShowScreen()
		self.TimerName += 1
		self.TimeBumpModes = timers.OnceTimer(2.0, name='ThermostatModes' + str(self.TimerName), proc=self.PushModes)
		self.TimeBumpModes.start()

	# push setpoint change after 2 seconds of idle

	# noinspection PyUnusedLocal
	def BumpFan(self, presstype):
		if self.TimeBumpFan is not None:
			self.TimeBumpFan.cancel()  # cancel any pending timer
		self.FanLocal = 0.5  # just do a show screen for mode and fan
		self.fanstates = self.fanstates[1:] + self.fanstates[:1]
		self.fan = self.fanstates[0]

		debug.debugPrint('Main', "Bump fan: ", self.fan)
		self.ShowScreen()
		self.TimerName += 1
		self.TimeBumpFan = timers.OnceTimer(2.0, name='ThermostatFan' + str(self.TimerName), proc=self.PushFanState)
		self.TimeBumpFan.start()

	# push setpoint change after 2 seconds of idle

	def ShowScreen(self):

		m = self.modes.index(self.mode)
		self.modes = self.modes[m:] + self.modes[:m]
		m = self.fanstates.index(self.fan)
		self.fanstates = self.fanstates[m:] + self.fanstates[:m]

		self.ReInitDisplay()

		r = fonts.fonts.Font(self.fsize[3], bold=True).render(u"{:4.1f}".format(self.t_cur), 0,
															  wc(self.CharColor))
		hw.screen.blit(r, ((hw.screenwidth - r.get_width()) // 2, self.TempPos))
		r = fonts.fonts.Font(self.fsize[0]).render(self.t_state.capitalize(), 0, wc(self.CharColor))
		hw.screen.blit(r, ((hw.screenwidth - r.get_width()) // 2, self.StatePos))
		rL = fonts.fonts.Font(self.fsize[2]).render("{:2d}".format(self.t_low), 0,
													wc(self.CharColor, factor=self.LocalOnly[0]))
		rH = fonts.fonts.Font(self.fsize[2]).render("{:2d}".format(self.t_high), 0,
													wc(self.CharColor, factor=self.LocalOnly[1]))
		hw.screen.blit(self.SetPointSurf, (self.SPHPosL - self.SPWdt // 2, self.SPVPos))
		hw.screen.blit(self.SetPointSurf, (self.SPHPosR - self.SPWdt // 2, self.SPVPos))
		hw.screen.blit(rL, (self.SPHPosL - self.SPWdt // 2, self.SPVPos))
		hw.screen.blit(rH, (self.SPHPosR - self.SPWdt // 2, self.SPVPos))
		hw.screen.blit(self.AdjButSurf, (0, self.AdjButTops))
		r1 = fonts.fonts.Font(self.fsize[1]).render(self.mode.capitalize(), 0,
													wc(self.CharColor, factor=self.ModeLocal))
		r2 = fonts.fonts.Font(self.fsize[1]).render(self.fan.capitalize(), 0, wc(self.CharColor, factor=self.FanLocal))
		hw.screen.blit(r1, (self.Keys['Mode'].Center[0] - r1.get_width() // 2, self.ModesPos))
		hw.screen.blit(r2, (self.Keys['Fan'].Center[0] - r2.get_width() // 2, self.ModesPos))
		pygame.display.update()

	def InitDisplay(self, nav):
		super(NestThermostatScreenDesc, self).InitDisplay(nav)
		self.t_cur, self.t_low, self.t_high, self.t_state, self.mode, self.fan = self.ThermNode.GetThermInfo()
		self.LocalOnly = [0.0, 0.0]
		self.ModeLocal = 0.0
		self.FanLocal = 0.0
		self.ShowScreen()

	def NodeEvent(self, hub='', node=0, value=0, varinfo=()):
		# need to verify that this is the real update?
		self.LocalOnly = [0.0, 0.0]
		self.ModeLocal = 0.0
		self.FanLocal = 0.0
		self.t_cur, self.t_low, self.t_high, self.t_state, self.mode, self.fan = self.ThermNode.GetThermInfo()
		if self.Active: self.ShowScreen()


screens.screentypes["NestThermostat"] = NestThermostatScreenDesc
