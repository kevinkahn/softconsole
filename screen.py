import collections

import pygame
import functools

import config
import debug
import fonts
import hubs.hubs
import hw
import logsupport
import screens.__screens as screens
import stores.paramstore as paramstore
import stores.valuestore as valuestore
import toucharea
import utilities
from logsupport import ConsoleError, ConsoleWarning, ConsoleDetail
from utilfuncs import wc, tint
import timers

ScreenParams = {'DimTO': 99,
				'CharColor': "white",
				'PersistTO': 20,
				'BackgroundColor': 'maroon',
				'CmdKeyCol': "red",
				'CmdCharCol': "white",
				'DefaultHub': '',
				'KeyColor': "aqua",
				'KeyColorOn': "",
				'KeyColorOff': "",
				'KeyCharColorOn': "white",
				'KeyCharColorOff': "black",
				'KeyOnOutlineColor': "white",
				'KeyOffOutlineColor': "black",
				'KeyOutlineOffset': 3,
				'KeyLabelOn': ['', ],
				'KeyLabelOff': ['', ],
				'ScreenTitleColor': "white",
				'ScreenTitleSize': 50,
				'ScreenTitle': '',
				'HorizBorder': 20,
				'TopBorder': 20,
				'BotBorder': 60,
				'BotBorderWONav': 20,
				'HorizButtonGap': 0,
				'VertButGap': 0,
				'NavKeyHeight': 60,
				'HorizButGap': 0,
				'NavKeyWidth': 60
				}

screenStore = valuestore.NewValueStore(paramstore.ParamStore('ScreenParams'))

screenparamuse = {}

BACKTOKEN = None
HOMETOKEN = None
SELFTOKEN = None

def InitScreenParams(parseconfig):
	screens.screenStore = screenStore
	for p, v in ScreenParams.items():
		screenStore.SetVal(p, type(v)(parseconfig.get(p, v)))


def GoToScreen(NS, newstate='NonHome'):
	screens.DS.SwitchScreen(NS, 'Bright', 'Go to Screen', newstate=newstate)


def PushToScreen(NS, newstate='NonHome', msg='Push to Screen'):
	screens.DS.SwitchScreen(NS, 'Bright', msg, newstate=newstate, push=True)


def PopScreen(msg='PopScreen', newstate='Maint'):
	screens.DS.SwitchScreen(BACKTOKEN, 'Bright', msg, newstate=newstate)


def IncorporateParams(this, clsnm, theseparams, screensection):
	paramset = set(theseparams)
	if type(this) not in screenparamuse:
		screenparamuse[type(this)] = {clsnm: paramset}
	else:
		screenparamuse[type(this)][clsnm] = paramset
	if screensection is None: screensection = {}
	for p in theseparams:
		if isinstance(theseparams, dict):
			if theseparams[p] is not None: this.userstore.SetVal(p, theseparams[p])
		else:
			if p in screensection:
				this.userstore.SetVal(p, type(ScreenParams[p])(screensection.get(p, "")))  # string only safe default


def AddUndefaultedParams(this, screensection, **kwargs):
	if screensection is None: screensection = {}
	for n, v in kwargs.items():
		if n in this.__dict__: del this.__dict__[n]  # remove if it was declared statically
		this.userstore.SetVal(n, type(v)(screensection.get(n, v)))


def FlatenScreenLabel(label):
	scrlabel = label[0]
	for s in label[1:]:
		scrlabel = scrlabel + " " + s
	return scrlabel


def ButLayout(butcount):
	#        1     2     3     4     5     6     7     8     9    10
	plan = ((1, 1), (1, 2), (1, 3), (2, 2), (1, 5), (2, 3), (2, 4), (2, 4), (3, 3), (4, 3),
			#       11    12    13    14    15    16    17    18    19    20
			(4, 3), (4, 3), (4, 4), (4, 4), (4, 4), (4, 4), (5, 4), (5, 4), (5, 4), (5, 4))
	if butcount in range(1, 21):
		return plan[butcount - 1]
	else:
		logsupport.Logs.Log("Button layout error - too many or no buttons: {}".format(butcount), severity=ConsoleError)
		return 5, 5


class ScreenDesc(object):
	"""
	Basic information about a screen, subclassed by all other screens to handle this information
	"""

	def __setattr__(self, key, value):
		if key not in ScreenParams:
			object.__setattr__(self, key, value)
		else:
			self.userstore.SetVal(key, value)

	# object.__setattr__(self, key, value)

	def __getattr__(self, key):
		return self.userstore.GetVal(key)

	def __init__(self, screensection, screenname, parentscreen=None, SingleUse=False, Clocked=0):
		self.userstore = paramstore.ParamStore('Screen-' + screenname,
											   dp=screenStore if parentscreen is None else parentscreen.userstore,
											   locname=screenname)
		# todo add routine to update allowable mods per screen - but rationalize with incorp parameters from hight level guys

		self.markradius = int(min(hw.screenwidth, hw.screenheight) * .025)

		self.name = screenname
		self.singleuse = SingleUse
		self.used = False
		self.Active = False  # true if actually on screen
		self.ScreenTimers = []
		self.ScreenClock = None
		self.DefaultNavKeysShowing = True
		self.NavKeysShowing = True
		self.NavKeys = collections.OrderedDict()
		self.Keys = collections.OrderedDict()
		self.WithNav = True
		self.useablevertspace = hw.screenheight - self.TopBorder - self.BotBorder
		self.useablevertspacesansnav = hw.screenheight - self.TopBorder - self.BotBorderWONav
		self.useablehorizspace = hw.screenwidth - 2 * self.HorizBorder
		self.startvertspace = self.TopBorder
		self.starthorizspace = self.HorizBorder
		self.titleoffset = 0
		self.HubInterestList = {}  # one entry per hub, each entry is a dict mapping addr to Node
		self.ScreenTitleBlk = None
		self.prevkey = None
		self.nextkey = None
		self.NavKeyWidth = (hw.screenwidth - 2 * self.HorizBorder) // 2
		if Clocked != 0:
			self.ScreenClock = timers.RepeatingPost(Clocked, paused=True, name='ScreenClock-' + self.name,
													proc=self._ClockTick, eventvalid=self._ClockTickValid)
			self.ScreenClock.start()

		cvertcenter = hw.screenheight - self.BotBorder / 2
		# print("NKW {} {} {} {}".format(self.NavKeyWidth, self.HorizBorder, self.HorizButGap, cvertcenter))

		self.homekey = toucharea.ManualKeyDesc(self, 'Back<' + 'Home', ('Home',),
											   self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
											   proc=functools.partial(GoToScreen, HOMETOKEN),
											   center=(
												   self.starthorizspace + .5 * (self.NavKeyWidth),
												   cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)
		self.backkey = toucharea.ManualKeyDesc(self, 'Nav>' + 'Back', ('Back',),
											   self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
											   proc=functools.partial(GoToScreen, BACKTOKEN),
											   center=(
												   self.starthorizspace + 1.5 * (self.NavKeyWidth),
												   cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)

		IncorporateParams(self, 'Screen',
						  {'CharColor', 'DimTO', 'PersistTO', 'BackgroundColor', 'CmdKeyCol', 'CmdCharCol',
						   'DefaultHub', 'ScreenTitle', 'ScreenTitleColor', 'ScreenTitleSize', 'KeyCharColorOn',
						   'KeyCharColorOff', 'KeyColor'}, screensection)
		AddUndefaultedParams(self, screensection, label=[screenname])
		try:
			self.DefaultHubObj = hubs.hubs.Hubs[self.DefaultHub]
		except KeyError:
			self.DefaultHubObj = None  # todo test what happens later or force this to be an exiting error
			logsupport.Logs.Log("Bad default hub name for screen: ", screenname, severity=ConsoleError)
			raise ValueError

		if self.ScreenTitle != '':
			# adjust space for a title
			self.ScreenTitleBlk = fonts.fonts.Font(self.ScreenTitleSize, bold=True).render(self.ScreenTitle, 0,
																						   wc(self.ScreenTitleColor))
			h = self.ScreenTitleBlk.get_height()
			w = self.ScreenTitleBlk.get_width()
			titlegap = h // 10  # todo is this the best way to space?
			self.startvertspace = self.startvertspace + h + titlegap
			self.useablevertspace = self.useablevertspace - h - titlegap
			self.useablevertspacesansnav = self.useablevertspacesansnav - h - titlegap
			self.titleoffset = self.starthorizspace + (self.useablehorizspace - w) // 2

		utilities.register_example('ScreenDesc', self)

	def _ClockTickValid(self, params):
		return self.Active

	def _ClockTick(self, params):  # todo make this a validity check and then call ClockTick directly as event.proc
		if not self.Active: return  # avoid race with timer and screen exit
		self.ClockTick()

	def ClockTick(self):  # this is meant to be overridden if screen want more complex operation
		self.ReInitDisplay()

	def CreateNavKeys(self, prevk, nextk):
		cvertcenter = hw.screenheight - self.BotBorder / 2
		self.prevkey = toucharea.ManualKeyDesc(self, 'Nav<' + prevk.name,
											   prevk.label,
											   prevk.CmdKeyCol, prevk.CmdCharCol,
											   prevk.CmdCharCol,
											   proc=functools.partial(GoToScreen, prevk),
											   center=(
												   self.starthorizspace + .5 * (
													   self.NavKeyWidth),
												   cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)
		self.nextkey = toucharea.ManualKeyDesc(self, 'Nav>' + nextk.name,
											   nextk.label,
											   nextk.CmdKeyCol, nextk.CmdCharCol,
											   nextk.CmdCharCol,
											   proc=functools.partial(GoToScreen, nextk),
											   center=(
												   self.starthorizspace + 1.5 * (
													   self.NavKeyWidth),
												   cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)

	def ClearScreenTitle(self):
		if self.ScreenTitleBlk is None: return
		h = self.ScreenTitleBlk.get_height()
		self.ScreenTitleBlk = None
		titlegap = h // 10
		self.startvertspace = self.startvertspace - h - titlegap
		self.useablevertspace = self.useablevertspace + h + titlegap
		self.useablevertspacesansnav = self.useablevertspacesansnav + h + titlegap

	def SetScreenTitle(self, name, fontsz, color, force=False):
		if self.ScreenTitleBlk is not None and not force:
			return  # User explicitly set a title so don't override it
		self.ClearScreenTitle()
		self.ScreenTitleBlk = fonts.fonts.Font(fontsz).render(name, 0, wc(color))
		h = self.ScreenTitleBlk.get_height()
		w = self.ScreenTitleBlk.get_width()
		titlegap = h // 10  # todo is this the best way to space? if fix - fix clear also
		self.startvertspace = self.startvertspace + h + titlegap
		self.useablevertspace = self.useablevertspace - h - titlegap
		self.useablevertspacesansnav = self.useablevertspacesansnav - h - titlegap
		self.titleoffset = self.starthorizspace + (self.useablehorizspace - w) // 2

	def ButSize(self, bpr, bpc, height):
		h = self.useablevertspace if height == 0 else height
		return (
			self.useablehorizspace / bpr, h / bpc)

	def PaintKeys(self):
		if self.Keys is not None:
			for key in self.Keys.values():
				if type(key) is not toucharea.TouchPoint:
					key.PaintKey()
		for key in self.NavKeys.values():
			key.PaintKey()

	def AddToHubInterestList(self, hub, item, value):
		if hub.name in self.HubInterestList:
			self.HubInterestList[hub.name][item] = value
		else:
			self.HubInterestList[hub.name] = {item: value}

	def InitDisplay(self, nav):
		if self.used:
			logsupport.Logs.Log('Attempted reuse (Init) of single use screen {}'.format(self.name),
								severity=ConsoleError)
		debug.debugPrint("Screen", "Base Screen InitDisplay: ", self.name)
		if self.ScreenClock is not None: self.ScreenClock.resume()
		self.PaintBase()
		self.NavKeys = nav
		self.PaintKeys()
		if self.ScreenTitleBlk is not None:
			hw.screen.blit(self.ScreenTitleBlk, (self.titleoffset, self.TopBorder))

	def ReInitDisplay(self):
		if self.used:
			logsupport.Logs.Log('Attempted reuse (ReInit) of single use screen {}'.format(self.name),
								severity=ConsoleError)
		self.PaintBase()
		self.PaintKeys()
		if self.ScreenTitleBlk is not None:
			hw.screen.blit(self.ScreenTitleBlk, (self.titleoffset, self.TopBorder))

	def NodeEvent(self, evnt):
		if evnt.node is not None:
			if evnt.hub != '*VARSTORE*':  # var changes can be reported while any screen is up
				logsupport.Logs.Log("Unexpected event to screen: ", self.name, ' Hub: ', str(evnt.hub), ' Node: ',
									str(evnt.node),
									' Val: ', str(evnt.value), severity=ConsoleDetail)
			else:
				pass
		else:
			logsupport.Logs.Log(
				'Node event to screen {} with no handler node: {} (Event: {})'.format(self.name, evnt.node, evnt),
				severity=ConsoleWarning, hb=True, tb=True)

	def VarEvent(self, evnt):
		pass  # var changes can happen with any screen up so if screen doesn't care about vars it doesn't define a handler

	# logsupport.Logs.Log('Var event to screen {} with no handler (Event: {})'.format(self.name,evnt), severity=ConsoleError)

	def ExitScreen(self, viaPush):
		if self.ScreenClock is not None: self.ScreenClock.pause()
		for timer in self.ScreenTimers:
			if timer.is_alive(): timer.cancel()
		self.ScreenTimers = []
		if self.singleuse:
			if viaPush:
				pass
			else:
				self.userstore.DropStore()
				for nm, k in self.Keys.items():
					if hasattr(k, 'userstore'): k.userstore.DropStore()
				for nm, k in self.NavKeys.items():
					if hasattr(k, 'userstore'): k.userstore.DropStore()
				self.used = True

	def DeleteScreen(self):
		# explicit screen destroy
		self.userstore.DropStore()
		if self.ScreenClock is not None: self.ScreenClock.cancel()
		for timer in self.ScreenTimers:
			if timer.is_alive(): timer.cancel()

	def PopOver(self):
		if self.singleuse:
			self.userstore.DropStore()
			for nm, k in self.Keys.items():
				k.userstore.DropStore()
			for nm, k in self.NavKeys.items():
				k.userstore.DropStore()
			self.used = True


	def PaintBase(self):
		hw.screen.fill(wc(self.BackgroundColor))
		lineclr = tint(self.BackgroundColor, tint_factor=.5)
		if config.sysStore.NetErrorIndicator:
			pygame.draw.circle(hw.screen, tint(self.BackgroundColor, tint_factor=.5),
							   (self.markradius, self.markradius), self.markradius, 0)
			lineclr = wc(self.BackgroundColor)
		if config.sysStore.ErrorNotice != -1:
			pygame.draw.line(hw.screen, lineclr, (0, self.markradius), (2 * self.markradius, self.markradius), 3)
			pygame.draw.line(hw.screen, lineclr, (self.markradius, 0), (self.markradius, 2 * self.markradius), 3)



class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname, parentscreen=None, SingleUse=False, Clocked=0):
		super().__init__(screensection, screenname, parentscreen=parentscreen, SingleUse=SingleUse, Clocked=Clocked)

		AddUndefaultedParams(self, screensection, KeysPerColumn=0, KeysPerRow=0)
		self.buttonsperrow = -1
		self.buttonspercol = -1
		utilities.register_example('BaseKeyScreenDesc', self)

	def LayoutKeys(self, extraOffset=0, height=0):
		# Compute the positions and sizes for the Keys and store in the Key objects
		explicitlayout = self.KeysPerColumn * self.KeysPerRow

		if explicitlayout != 0:
			# user provided explicit button layout
			if explicitlayout >= len(self.Keys):
				# user layout provides enough space
				bpr, bpc = (self.KeysPerRow, self.KeysPerColumn)
			else:
				# bad user layout - go with automatic
				logsupport.Logs.Log('Bad explicit key layout for: ', self.name, severity=ConsoleWarning)
				bpr, bpc = ButLayout(len(self.Keys))
		else:
			bpr, bpc = ButLayout(
				len(self.Keys))  # don't do this if explicit layout spec's because may be more keys than it can handle

		self.buttonsperrow = bpr
		self.buttonspercol = bpc

		buttonsize = self.ButSize(bpr, bpc, height)
		hpos = []
		vpos = []
		for i in range(bpr):
			hpos.append(self.starthorizspace + (.5 + i) * buttonsize[0])
		for i in range(bpc):
			vpos.append(self.startvertspace + extraOffset + (.5 + i) * buttonsize[1])

		for i, (kn, key) in enumerate(self.Keys.items()):
			key.FinishKey((hpos[i % bpr], vpos[i // bpr]), buttonsize)
