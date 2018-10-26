import pygame
import logsupport
import supportscreens
from logsupport import ConsoleWarning, ConsoleError
from utilfuncs import wc
import hasshub  # only to test that the hub for this is an HA hub

import config
import debug
import screen
import screenutil
import utilities
import toucharea
import functools


class SonosScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		self.numplayers = 0  # if 0 then Sonos didn't get set up correctly
		self.KeyColor = ''
		self.PlayerInputs = []
		debug.debugPrint('Screen', "New SonosScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor')
		self.DullKeyColor = wc(self.KeyColor, .5, self.BackgroundColor)
		self.HA = self.DefaultHub
		self.HubInterestList[self.HA.name] = {}
		self.title, th, self.tw = screenutil.CreateTextBlock('Sonos', config.screenheight / 12, self.CharColor, True)
		self.titlespace = th + config.screenheight / 32
		useablescreenheight = config.screenheight - config.topborder - config.botborder - self.titlespace
		self.SonosNodes = {}
		self.NodeVPos = []
		self.KeysSum = {}
		self.GCVPos = []
		self.KeysGC = {}
		self.KeysGpCtl = {}
		self.GPCtlVPos = []
		self.SrcSlotsVPos = []
		self.KeysSrc = {}
		self.ButLocSize = []
		self.SonosGroups = {}
		self.RoomNames = {}
		self.SlotToGp = []
		self.Subscreen = -1
		self.SourceItem = 0
		self.SourceSelection = ''
		self.ExtraSource = {}
		if isinstance(self.DefaultHub, hasshub.HA):
			for n, p in self.HA.MediaPlayers.items():
				if p.Sonos:
					self.SonosNodes[p.entity_id] = p
					self.SlotToGp.append('')
					self.HubInterestList[self.HA.name][p.entity_id] = p.entity_id
		else:
			logsupport.Logs.Log("Sonos Default Hub is not HA hub", severity=ConsoleError, tb=False)
			return
		self.numplayers = len(self.SonosNodes)
		if self.numplayers == 0:
			logsupport.Logs.Log("No Sonos Players reported - check network", severity=ConsoleError)
			return

		# set up source selection screen
		self.SourceSlot = []
		vpos = self.titlespace
		self.sourceslots = 8
		self.sourceheight = useablescreenheight // (self.sourceslots + 1)  # allow space at bottom right for arrow

		for i in range(self.sourceslots):
			self.SrcSlotsVPos.append(vpos)
			self.KeysSrc['Src' + str(i)] = toucharea.TouchPoint('Scr' + str(i),
																(
																config.screenwidth // 2, vpos + self.sourceheight // 2),
																(config.screenwidth, self.sourceheight),
																proc=functools.partial(self.PickSource, i))
			vpos += self.sourceheight
			self.SourceSlot.append('')
		self.SrcPrev = (
		config.screenwidth - self.sourceheight - config.horizborder, self.titlespace - self.sourceheight // 2)
		self.SrcNext = (config.screenwidth - self.sourceheight - config.horizborder,
						vpos + self.sourceheight // 2 + 10)  # for appearance
		self.KeysSrc['Prev'] = toucharea.TouchPoint('Prev' + str(i), self.SrcPrev,
													(self.sourceheight, self.sourceheight),
													proc=functools.partial(self.PrevNext, False))
		self.KeysSrc['Next'] = toucharea.TouchPoint('Next' + str(i), self.SrcNext,
													(self.sourceheight, self.sourceheight),
													proc=functools.partial(self.PrevNext, True))
		self.KeysSrc['OKSrc'] = toucharea.ManualKeyDesc(screen, 'OKSrc', ['OK'], self.BackgroundColor,
														self.CharColor, self.CharColor,
														center=(
														self.SrcNext[0] - 2.5 * self.sourceheight, self.SrcNext[1]),
														size=(2 * self.sourceheight, self.sourceheight), KOn='',
														KOff='',
														proc=functools.partial(self.PickSourceOK, True))
		self.KeysSrc['CnclSrc'] = toucharea.ManualKeyDesc(screen, 'CnclSrc', ['Back'], self.BackgroundColor,
														  self.CharColor, self.CharColor,
														  center=(
														  self.SrcNext[0] - 5 * self.sourceheight, self.SrcNext[1]),
														  size=(2 * self.sourceheight, self.sourceheight), KOn='',
														  KOff='',
														  proc=functools.partial(self.PickSourceOK, False))

		for i in range(self.numplayers + 1):
			self.GCVPos.append(self.titlespace + i * 50)

		# set up the control screen for a group
		self.ctlhgt = useablescreenheight // (2 * self.numplayers + 2)
		for i in range(self.numplayers + 1):
			self.GPCtlVPos.append(self.titlespace + i * 2 * self.ctlhgt)

		# set up the main summary screen
		vpos = self.titlespace
		self.roomheight = useablescreenheight // self.numplayers
		self.roomdisplayinfo = (1.5, 1, 1, 1)
		for n, p in self.SonosNodes.items():
			self.NodeVPos.append(vpos)
			vpos += self.roomheight
			lineheight = self.roomheight / (sum(self.roomdisplayinfo) / self.roomdisplayinfo[0])
			self.RoomNames[p.entity_id] = screenutil.CreateTextBlock(p.FriendlyName, lineheight, self.CharColor, True,
																	 FitLine=True)
		self.NodeVPos.append(vpos)

		for i in range(self.numplayers):
			self.KeysSum['Slot' + str(i)] = toucharea.TouchPoint('Slot' + str(i),
																 (config.screenwidth // 2,
																  (self.NodeVPos[i] + self.NodeVPos[i + 1]) // 2),
																 (config.screenwidth, self.roomheight),
																 proc=functools.partial(self.RoomSelect, i))
			self.KeysGC['SlotGC' + str(i)] = toucharea.TouchPoint('SlotGC' + str(i),
																  (config.screenwidth // 2,
																   (self.GCVPos[i] + self.GCVPos[i + 1]) // 2),
																  (config.screenwidth, 50),
																  proc=functools.partial(self.GroupMemberToggle, i))
			butvert = self.GPCtlVPos[i] + self.ctlhgt * 1.5
			butsz = (self.ctlhgt, self.ctlhgt)
			self.ButLocSize.append({'Dn': ((config.screenwidth // 4, butvert), butsz)})
			self.KeysGpCtl['Dn' + str(i)] = toucharea.TouchPoint('Dn' + str(i), (config.screenwidth // 4, butvert),
																 butsz,
																 proc=functools.partial(self.VolChange, i, -1))

			self.ButLocSize[i]['Up'] = ((config.screenwidth // 2, butvert), butsz)
			self.KeysGpCtl['Up' + str(i)] = toucharea.TouchPoint('Up' + str(i), (config.screenwidth // 2, butvert),
																 butsz,
																 proc=functools.partial(self.VolChange, i, 1))

			self.ButLocSize[i]['Mute'] = ((3 * config.screenwidth // 4, butvert), butsz)
			self.KeysGpCtl['Mute' + str(i)] = toucharea.TouchPoint('Mute' + str(i),
																   (3 * config.screenwidth // 4, butvert), butsz,
																   proc=functools.partial(self.VolChange, i, 0))

		self.KeysGpCtl['Source'] = toucharea.ManualKeyDesc(screen, 'Source', ['Source'], self.BackgroundColor,
														   self.CharColor, self.CharColor,
														   center=(3 * config.screenwidth // 4,
																   self.GPCtlVPos[-1] + self.ctlhgt),
														   size=(config.screenwidth // 3, self.ctlhgt), KOn='', KOff='',
														   proc=self.SetSource)

		self.KeysGpCtl['OKCtl'] = toucharea.ManualKeyDesc(screen, 'OKCtl', ['OK'], self.BackgroundColor,
														  self.CharColor, self.CharColor,
														  center=(
														  config.screenwidth // 4, self.GPCtlVPos[-1] + self.ctlhgt),
														  size=(config.screenwidth // 3, self.ctlhgt), KOn='', KOff='',
														  proc=self.GpCtlOK)

		self.KeysGC['OK'] = toucharea.ManualKeyDesc(screen, 'OK', ['OK'], self.BackgroundColor,
													self.CharColor, self.CharColor,
													center=(config.screenwidth // 2, self.GCVPos[-1] + 30),
													size=(config.screenwidth // 4, self.ctlhgt), KOn='', KOff='',
													proc=self.GroupMemberOK)

		self.Keys = self.KeysSum
		utilities.register_example("SonosScreenDesc", self)

	def NodeEvent(self, hub='', node=0, value=0, varinfo=()):
		# Watched node reported change event is ("Node", addr, value, seq)
		# print('event')  todo should check that event is for a Sonos node?
		stable = self.UpdateGroups()
		if stable:
			#print('stable')
			self.ShowScreen()

	def VolChange(self, slotnum, chg, presstype):
		if slotnum >= len(self.nms): return
		rm = self.nms[slotnum]
		if chg == 0:
			rm.Mute(rm.entity_id, not rm.muted)
		else:
			rm.VolumeUpDown(rm.entity_id, chg)

	def GpCtlOK(self, presstype):
		self.Subscreen = -1
		self.ShowScreen()

	def SetSource(self, presstype):
		self.Subscreen = self.Subscreen + 200
		self.SourceSelection = ''
		self.SourceSet = self.SonosNodes[self.SlotToGp[self.Subscreen - 200]].source_list[:]
		self.SourceItem = 0
		self.ShowScreen()

	def PickSource(self, slotnum, presstype):
		#print(slotnum)
		# change the source
		self.SourceSelection = self.SourceSlot[slotnum]
		self.ShowScreen()

	def PickSourceOK(self, doit, presstype):
		if doit:
			self.SonosNodes[self.SlotToGp[self.Subscreen - 200]].Source(self.SlotToGp[self.Subscreen - 200],
																		self.SourceSelection)
		self.Subscreen = self.Subscreen - 200
		self.SourceSelection = ''
		self.ShowScreen()

	def PrevNext(self, nxt, presstype):
		if nxt:
			if self.SourceItem + self.sourceslots < len(self.SourceSet):
				self.SourceItem += self.sourceslots
		elif self.SourceItem - self.sourceslots >= 0:
			self.SourceItem -= self.sourceslots
		self.ShowScreen()

	def RoomSelect(self, slotnum, presstype):
		if presstype:
			# Double tap
			self.Subscreen = 100 + slotnum
		else:
			self.Subscreen = slotnum
		self.ShowScreen()

	def GroupMemberOK(self, presstype):
		self.Subscreen = -1
		self.ShowScreen()

	def GroupMemberToggle(self, slotnum, presstype):
		if self.gpingrms[slotnum][1]:
			# unjoin it
			self.gpingrms[0][0].UnJoin(self.gpingrms[slotnum][0].entity_id)
		else:
			# join to this master
			self.gpingrms[0][0].Join(self.gpingrms[0][0].entity_id, self.gpingrms[slotnum][0].entity_id)
			pass
		# self.Subscreen = -1
		self.ShowScreen()

	def UpdateGroups(self):
		assigned = 0
		gpassign = {}
		for n, p in self.SonosNodes.items():
			if p.sonos_group[0] == n:  # we are a group master
				if p.internalstate != -1:
					# if node went unavailable skip this to keep lsst state of groups for now
					self.SonosGroups[n] = p.attributes['sonos_group']
				assigned += len(self.SonosGroups[n])
			else:
				if n in self.SonosGroups: del self.SonosGroups[n]
		self.numgroups = len(self.SonosGroups)
		return assigned == self.numplayers

	def InitDisplay(self, nav):
		super(SonosScreenDesc, self).InitDisplay(nav)
		self.Subscreen = -1
		self.ShowScreen()

	def SummaryScreen(self):
		if self.numplayers == 0:
			errmsg, _, _ = screenutil.CreateTextBlock([' ', 'No Players', 'Found', 'Check', 'Configuration', ' '], 30,
													  'white', True)
			config.screen.blit(errmsg, (config.horizborder + 15, 40))
			pygame.display.update()
			return
		self.Keys = self.KeysSum
		self.ReInitDisplay()
		slot = 0
		pygame.draw.line(config.screen, wc(self.CharColor), (config.horizborder, self.NodeVPos[0]),
						 (config.screenwidth - config.horizborder, self.NodeVPos[0]), 3)
		for e, g in self.SonosGroups.items():
			ginfo = self.SonosNodes[g[0]]
			if ginfo.internalstate == -1:
				unav, ht, wd = screenutil.CreateTextBlock('<player info unavailable>',
														  self.roomheight // (
																  sum(self.roomdisplayinfo) / self.roomdisplayinfo[1]),
														  self.CharColor, False, FitLine=True
														  , MaxWidth=config.screenwidth - 2 * config.horizborder - 15)
				config.screen.blit(unav, (config.horizborder + 15,
										  self.NodeVPos[slot] + self.roomheight // (
												  sum(self.roomdisplayinfo) / self.roomdisplayinfo[0])))
			else:
				song, ht, wd = screenutil.CreateTextBlock([ginfo.song, ginfo.artist, ginfo.album],
														  self.roomheight // (
																  sum(self.roomdisplayinfo) / self.roomdisplayinfo[1]),
														  self.CharColor, False, FitLine=True
														  , MaxWidth=config.screenwidth - 2 * config.horizborder - 15)
				config.screen.blit(song, (config.horizborder + 15,
										  self.NodeVPos[slot] + self.roomheight // (
												  sum(self.roomdisplayinfo) / self.roomdisplayinfo[0])))
			for n in g:
				config.screen.blit(self.RoomNames[n][0], (config.horizborder + 5, self.NodeVPos[slot]))
				self.SlotToGp[slot] = e
				slot += 1
				lineoff = self.NodeVPos[slot]
			pygame.draw.line(config.screen, wc(self.CharColor), (config.horizborder, lineoff),
							 (config.screenwidth - config.horizborder, lineoff), 3)
		pygame.draw.line(config.screen, wc(self.CharColor), (config.horizborder, self.NodeVPos[0]),
						 (config.horizborder, lineoff), 3)
		pygame.draw.line(config.screen, wc(self.CharColor), (config.screenwidth - config.horizborder, self.NodeVPos[0]),
						 (config.screenwidth - config.horizborder, lineoff), 3)

	def _Speaker(self, c, hgt):
		h = .8 * hgt
		left = c[0] - h // 2
		right = c[0] + h // 2
		top = c[1] - h // 2
		bot = c[1] + h // 2
		qup = c[1] - h // 4
		qdn = c[1] + h // 4
		return ((left, qup), (c[0], qup), (right - h // 4, top), (right - h // 4, bot), (c[0], qdn), (left, qdn)), (
		(left, bot), (right, top))

	def GroupScreen(self, gpentity):

		self.nms = []
		self.Keys = self.KeysGpCtl
		self.ReInitDisplay()
		i = 0
		for p in self.SonosGroups[gpentity]:
			self.nms.append(self.SonosNodes[p])
			rn = screenutil.CreateTextBlock(self.nms[-1].FriendlyName, self.ctlhgt, self.CharColor, True, FitLine=True,
											MaxWidth=config.screenwidth - 2 * config.horizborder + 10)
			vol = self.nms[-1].volume * 100
			volrndr, h, w = screenutil.CreateTextBlock(str(int(vol)), .8 * self.ctlhgt, self.CharColor, True,
													   FitLine=True)
			volx = (self.ButLocSize[i]['Dn'][0][0] + self.ButLocSize[i]['Up'][0][0] - w) // 2
			config.screen.blit(volrndr, (volx, self.ButLocSize[i]['Dn'][0][1] - h // 2))
			config.screen.blit(rn[0], (20, self.GPCtlVPos[i]))
			pygame.draw.polygon(config.screen, wc(self.CharColor),
								supportscreens._TriangleCorners(self.ButLocSize[i]['Dn'][0],
																self.ButLocSize[i]['Dn'][1][0],
																True), 2)
			pygame.draw.polygon(config.screen, wc(self.CharColor),
								supportscreens._TriangleCorners(self.ButLocSize[i]['Up'][0],
																self.ButLocSize[i]['Up'][1][0],
																False), 2)
			spkr, diagbar = self._Speaker(self.ButLocSize[i]['Mute'][0], self.ButLocSize[i]['Mute'][1][0])
			pygame.draw.polygon(config.screen, wc(self.CharColor), spkr, 2)
			if self.nms[-1].muted:
				pygame.draw.line(config.screen, wc(self.CharColor), diagbar[0], diagbar[1], 4)
			i += 1

	def ChangeGroupingScreen(self, gpentity):
		self.Keys = self.KeysGC
		self.ReInitDisplay()
		self.gpingrms = [[self.SonosNodes[gpentity], True]]
		for n, r in self.SonosNodes.items():
			if n != gpentity:
				ingp = n in self.SonosNodes[gpentity].sonos_group
				self.gpingrms.append([r, ingp])
		for rm, i in zip(self.gpingrms, range(self.numplayers)):
			config.screen.blit(screenutil.CreateTextBlock(rm[0].FriendlyName, 40,
														  (self.DullKeyColor, self.CharColor)[rm[1]], False,
														  FitLine=True,
														  MaxWidth=config.screenwidth - config.horizborder)[0],
							   (20, self.GCVPos[i]))


	def SourceSelectScreen(self):
		# show a list of sources starting with startsource item last item is either next or return
		# compute sources per screen as usable vertical height div item pixel height
		self.Keys = self.KeysSrc
		self.ReInitDisplay()
		for i in range(self.SourceItem, min(len(self.SourceSet), self.SourceItem + self.sourceslots)):
			slot = i - self.SourceItem
			clr = self.DullKeyColor if self.SourceSet[i] == self.SourceSelection else self.CharColor
			rs, h, w = screenutil.CreateTextBlock(self.SourceSet[i], self.sourceheight, clr, False, FitLine=True,
												  MaxWidth=config.screenwidth - config.horizborder * 2)
			self.SourceSlot[slot] = self.SourceSet[i]
			voff = self.SrcSlotsVPos[slot] + (self.sourceheight - h) // 2
			config.screen.blit(rs, (config.horizborder, voff))
		pygame.draw.polygon(config.screen, wc(self.CharColor),
							supportscreens._TriangleCorners(self.SrcPrev, self.sourceheight,
															False), 3)
		pygame.draw.polygon(config.screen, wc(self.CharColor),
							supportscreens._TriangleCorners(self.SrcNext, self.sourceheight,
															True), 3)

	def ShowScreen(self):
		stable = self.UpdateGroups()
		# self.ReInitDisplay()
		if self.numplayers == 0:
			pass  # no players - probably startup sequencing error
		elif self.Subscreen == -1:
			self.SummaryScreen()
		elif self.Subscreen >= 100 and self.Subscreen < 200:
			self.ChangeGroupingScreen(self.SlotToGp[self.Subscreen - 100])
		elif self.Subscreen >= 200:
			self.SourceSelectScreen()
		else:
			self.GroupScreen(self.SlotToGp[self.Subscreen])
		config.screen.blit(self.title, ((config.screenwidth - self.tw) / 2, 0))

		pygame.display.update()


config.screentypes["Sonos"] = SonosScreenDesc
