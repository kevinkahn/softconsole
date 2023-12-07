import collections

from guicore.screencallmanager import pg
import functools
from guicore.switcher import SwitchScreen
import config
import hubs.hubs
import logsupport
import screens.__screens as screens
import stores.paramstore as paramstore
import stores.valuestore as valuestore
from keyspecs import toucharea
from logsupport import ConsoleError, ConsoleWarning
from utils.utilfuncs import wc, fmt
from utils import timers, utilities, fonts, displayupdate, hw
from utils.utilfuncs import safeprint
from config import ItemTypes

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
				'ScreenTitleFields': ['', ],
				'HorizBorder': 20,
				'TopBorder': 20,
				'BotBorder': 60,
				'BotBorderWONav': 20,
				'HorizButtonGap': 0,
				'VertButGap': 0,
				'NavKeyHeight': 60,
				'HorizButGap': 0,
				'NavKeyWidth': 60,
				'TitleBold': True}

screenStore = valuestore.NewValueStore(paramstore.ParamStore('ScreenParams'))

BACKTOKEN = None
HOMETOKEN = None
SELFTOKEN = None


def CommonClockTick(params):
	# noinspection PyProtectedMember
	config.AS._ClockTick(params)


# noinspection PyProtectedMember
def CommonClockTickValid():
	return config.AS._ClockTickValid()


StdScreenClock = 1

# noinspection PyTypeChecker
ScreenClocks = {StdScreenClock: timers.RepeatingPost(StdScreenClock, paused=True, start=True, name='StdScreenClock',
													 proc=CommonClockTick, eventvalid=CommonClockTickValid)}
RunningScreenClock = ScreenClocks[StdScreenClock]


def InitScreenParams(parseconfig):
	screens.screenStore = screenStore
	for p, v in ScreenParams.items():
		screenStore.SetVal(p, type(v)(parseconfig.get(p, v)))


def GoToScreen(NS, newstate='NonHome'):
	SwitchScreen(NS, 'Bright', 'Go to Screen', newstate=newstate)


def PushToScreen(NS, newstate='NonHome', msg='Push to Screen'):
	SwitchScreen(NS, 'Bright', msg, newstate=newstate, push=True)


def PopScreen(msg='PopScreen', newstate='Maint'):
	SwitchScreen(BACKTOKEN, 'Bright', msg, newstate=newstate)


# noinspection PyUnusedLocal
def IncorporateParams(this, clsnm, theseparams, screensection):
	if screensection is None:
		screensection = {}
	for p in theseparams:
		if isinstance(theseparams, dict):
			if theseparams[p] is not None:
				this.userstore.SetVal(p, theseparams[p])  # a value was set in config file
		else:
			if p in screensection:
				# this.userstore.SetVal(p, type(ScreenParams[p])(screensection.get(p, "")))  # string only safe default
				this.userstore.SetVal(p, type(ScreenParams[p])(screensection.get(p, ScreenParams[p])))


def AddUndefaultedParams(this, screensection, **kwargs):
	if screensection is None:
		screensection = {}
	if type(this).__name__ not in ItemTypes:
		ItemTypes[type(this).__name__] = set()
	for n, v in kwargs.items():
		ItemTypes[type(this).__name__].add(n)
	for n, v in kwargs.items():
		if n in this.__dict__:
			del this.__dict__[n]  # remove if it was declared statically
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

	def __init__(self, screensection, screenname, parentscreen=None, SingleUse=False, Type='unset'):
		self.userstore = paramstore.ParamStore('Screen-' + screenname,
											   dp=screenStore if parentscreen is None else parentscreen.userstore,
											   locname=screenname)
		# todo add routine to update allowable mods per screen - but rationalize with incorp parameters from hight level guys

		self.ScreenType = Type
		self.markradius = int(min(hw.screenwidth, hw.screenheight) * .025)
		self.name = screenname
		self.singleuse = SingleUse
		self.used = False
		self.WatchMotion = False
		self.Active = False  # true if actually on screen
		self.ChildScreens = {}  # used to do cascaded deleted if this screen is deleted. Only list one-off dependents

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
		self.HubInterestList = {}  # one entry per hub, each entry is a dict mapping addr to Node

		self.ScreenTitleBlk = None
		self.ScreenTitle = ''
		self.prevkey = None
		self.nextkey = None
		self.NavKeyWidth = (hw.screenwidth - 2 * self.HorizBorder) // 2

		cvertcenter = hw.screenheight - self.BotBorder / 2

		self.homekey = toucharea.ManualKeyDesc(self, 'Back<' + 'Home', ('Home',),
											   self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
											   proc=functools.partial(GoToScreen, HOMETOKEN),
											   center=(self.starthorizspace + .5 * self.NavKeyWidth, cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)
		self.backkey = toucharea.ManualKeyDesc(self, 'Nav>' + 'Back', ('Back',),
											   self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
											   proc=functools.partial(GoToScreen, BACKTOKEN),
											   center=(self.starthorizspace + 1.5 * self.NavKeyWidth, cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)

		IncorporateParams(self, 'Screen',
						  {'CharColor', 'DimTO', 'PersistTO', 'BackgroundColor', 'CmdKeyCol', 'CmdCharCol',
						   'DefaultHub', 'ScreenTitle', 'ScreenTitleColor', 'ScreenTitleFields', 'ScreenTitleSize',
						   'KeyCharColorOn',
						   'KeyCharColorOff', 'KeyColor', 'TitleBold'}, screensection)
		AddUndefaultedParams(self, screensection, label=[screenname])
		try:
			self.DefaultHubObj = hubs.hubs.Hubs[self.DefaultHub]
		except KeyError:
			self.DefaultHubObj = None  # todo test what happens later or force this to be an exiting error
			logsupport.Logs.Log("Bad default hub name for screen: ", screenname, severity=ConsoleError)
			raise ValueError

		self.DecodedScreenTitleFields = []
		for f in self.ScreenTitleFields:
			if ':' in f:
				self.DecodedScreenTitleFields.append(f.split(':'))

		# todo compute the vertical space issue for the title if non-null; generate and horiz space the title later
		if self.ScreenTitle != '':
			# adjust space for a title
			tempblk, _ = self._GenerateTitleBlk(self.ScreenTitle, self.DecodedScreenTitleFields, self.ScreenTitleColor)
			h = tempblk.get_height()
			titlegap = h // 10  # todo is this the best way to space?
			self.startvertspace = self.startvertspace + h + titlegap
			self.useablevertspace = self.useablevertspace - h - titlegap
			self.useablevertspacesansnav = self.useablevertspacesansnav - h - titlegap

			self.ScreenTitleBlk = tempblk

		self.ScreenClock = ScreenClocks[StdScreenClock]
		self.ScreenTimers = []  # (Timer, Cancel Proc, or None)  Don't put ScreenCLock in the list, or it gets canceled

		utilities.register_example('ScreenDesc', self)

	def _GenerateTitleBlk(self, title, fields, color):
		vals = ['--' if v is None else v for v in
				[valuestore.GetVal(f) for f in fields]]
		formattedTitle = fmt.format(title, *vals)
		blk = fonts.fonts.Font(self.ScreenTitleSize, bold=self.TitleBold).render(formattedTitle, 0, wc(color))
		w = blk.get_width()
		return blk, w

	def _ClockTickValid(self):
		if not self.Active:
			safeprint('Clock not valid {}'.format(self.name))
		return self.Active

	# noinspection PyUnusedLocal
	def _ClockTick(self, params):
		if not self.Active:
			return  # avoid race with timer and screen exit
		self.ClockTick()

	def ClockTick(self):  # this is meant to be overridden if screen want more complex operation
		self.ReInitDisplay()

	def SetScreenClock(self, interval):
		# for screens with a non-standard clocking rate

		if interval in ScreenClocks:
			self.ScreenClock = ScreenClocks[interval]
		else:
			# noinspection PyTypeChecker
			self.ScreenClock = timers.RepeatingPost(interval, paused=True, start=True,
													name='ScreenClock-' + str(interval),
													proc=CommonClockTick, eventvalid=CommonClockTickValid)
			ScreenClocks[interval] = self.ScreenClock

	def CreateNavKeys(self, prevk, nextk):
		cvertcenter = hw.screenheight - self.BotBorder / 2
		self.prevkey = toucharea.ManualKeyDesc(self, 'Nav<' + prevk.name,
											   prevk.label,
											   prevk.CmdKeyCol, prevk.CmdCharCol,
											   prevk.CmdCharCol,
											   proc=functools.partial(GoToScreen, prevk),
											   center=(self.starthorizspace + .5 * self.NavKeyWidth, cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)
		self.nextkey = toucharea.ManualKeyDesc(self, 'Nav>' + nextk.name,
											   nextk.label,
											   nextk.CmdKeyCol, nextk.CmdCharCol,
											   nextk.CmdCharCol,
											   proc=functools.partial(GoToScreen, nextk),
											   center=(self.starthorizspace + 1.5 * self.NavKeyWidth, cvertcenter),
											   size=(self.NavKeyWidth, self.NavKeyHeight), gaps=True)

	def ClearScreenTitle(self):
		if self.ScreenTitleBlk is None:
			return
		h = self.ScreenTitleBlk.get_height()
		self.ScreenTitleBlk = None
		self.ScreenTitle = ''
		titlegap = h // 10
		self.startvertspace = self.startvertspace - h - titlegap
		self.useablevertspace = self.useablevertspace + h + titlegap
		self.useablevertspacesansnav = self.useablevertspacesansnav + h + titlegap

	def SetScreenTitle(self, name, fontsz, color, force=False):
		if self.ScreenTitleBlk is not None and not force:
			return  # User explicitly set a title so don't override it
		self.ClearScreenTitle()
		self.ScreenTitle = name
		self.ScreenTitleBlk = fonts.fonts.Font(fontsz).render(name, 0, wc(color))
		h = self.ScreenTitleBlk.get_height()
		titlegap = h // 10  # todo is this the best way to space? if fix - fix clear also
		self.startvertspace = self.startvertspace + h + titlegap
		self.useablevertspace = self.useablevertspace - h - titlegap
		self.useablevertspacesansnav = self.useablevertspacesansnav - h - titlegap

	def ButSize(self, bpr, bpc, height):
		h = self.useablevertspace if height == 0 else height
		return (
			self.useablehorizspace / bpr, h / bpc)

	def PaintNavKeys(self):
		for key in self.NavKeys.values():
			key.PaintKey()

	def PaintKeys(self):
		if self.Keys is not None:
			for key in self.Keys.values():
				if type(key) is not toucharea.TouchPoint:
					key.PaintKey()
		self.PaintNavKeys()

	def ScreenContentRepaint(self):
		pass

	def AddToHubInterestList(self, hub, item, value):
		if hub.name in self.HubInterestList:
			self.HubInterestList[hub.name][item] = value
		else:
			self.HubInterestList[hub.name] = {item: value}

	def _PrepScreen(self, nav=None, init=True):
		global RunningScreenClock
		if self.used:
			logsupport.Logs.Log('Attempted reuse (Init: {}) of single use screen {}'.format(init, self.name),
								severity=ConsoleError)
		if init:
			if self.ScreenClock != RunningScreenClock:
				RunningScreenClock.pause()
				self.ScreenClock.resume()
				RunningScreenClock = self.ScreenClock
			else:
				RunningScreenClock.resume()

		if init:
			self.NavKeys = nav
		self.PaintBase()
		self.PaintKeys()
		if self.ScreenTitleBlk is not None:
			self.ScreenTitleBlk, w = self._GenerateTitleBlk(self.ScreenTitle, self.DecodedScreenTitleFields,
															self.ScreenTitleColor)
			hw.screen.blit(self.ScreenTitleBlk,
						   (self.starthorizspace + (self.useablehorizspace - w) // 2, self.TopBorder))
		self.ScreenContentRepaint()
		displayupdate.updatedisplay()

	def InitDisplay(self, nav):
		self._PrepScreen(nav, True)

	def ReInitDisplay(self):
		self._PrepScreen(None, False)

	def NodeEvent(self, evnt):
		if evnt.node is not None:
			if evnt.hub != '*VARSTORE*':  # var changes can be reported while any screen is up
				logsupport.Logs.Log("Unexpected event to screen: ", self.name, ' Hub: ', str(evnt.hub), ' Node: ',
									str(evnt.node),
									' Val: ', str(evnt.value))  # , severity=ConsoleDetail)
			else:
				pass
		else:
			logsupport.Logs.Log(
				'Node event to screen {} with no handler node: {} (Event: {})'.format(self.name, evnt.node, evnt),
				severity=ConsoleWarning, hb=True, tb=True)

	def VarEvent(self, evnt):
		pass  # var changes can happen with any screen up so if screen doesn't care about vars it doesn't define a handler

	def ExitScreen(self, viaPush):
		if self.ScreenClock is not None:
			self.ScreenClock.pause()
		for timer in self.ScreenTimers:
			if timer[0].is_alive():
				timer[0].cancel()
				if timer[1] is not None:
					timer[1]()
		self.ScreenTimers = []
		if self.singleuse:
			if viaPush:
				pass
			else:
				self.userstore.DropStore()
				for nm, k in self.Keys.items():
					if hasattr(k, 'userstore'):
						k.userstore.DropStore()
				for nm, k in self.NavKeys.items():
					if hasattr(k, 'userstore'):
						k.userstore.DropStore()
				self.used = True

	def DeleteScreen(self):
		# explicit screen destroy
		self.userstore.DropStore()
		for timer in self.ScreenTimers:
			if timer[0].is_alive():
				timer[0].cancel()
				if timer[1] is not None:
					timer[1]()
		for n, s in self.ChildScreens.items():
			s.DeleteScreen()

	def PopOver(self):
		try:
			if self.singleuse:
				self.userstore.DropStore()
				for nm, k in self.Keys.items():
					k.userstore.DropStore()
				for nm, k in self.NavKeys.items():
					k.userstore.DropStore()
				self.used = True
		except Exception as E:
			logsupport.Logs.Log('Screen sequencing exception for screen {}: {}'.format(self.name, repr(E)),
								severity=ConsoleWarning)

	def PaintBase(self):
		hw.screen.fill(wc(self.BackgroundColor))
		lineclr = wc(self.BackgroundColor, factor=.5)
		if config.sysStore.NetErrorIndicator:
			pg.draw.circle(hw.screen, wc(self.BackgroundColor, factor=.5),
						   (self.markradius, self.markradius), self.markradius, 0)
			lineclr = wc(self.BackgroundColor)
		if config.sysStore.ErrorNotice != -1:
			pg.draw.line(hw.screen, lineclr, (0, self.markradius), (2 * self.markradius, self.markradius), 3)
			pg.draw.line(hw.screen, lineclr, (self.markradius, 0), (self.markradius, 2 * self.markradius), 3)


class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname, parentscreen=None, SingleUse=False):
		super().__init__(screensection, screenname, parentscreen=parentscreen, SingleUse=SingleUse)

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
