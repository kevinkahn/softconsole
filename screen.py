import collections

import pygame

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
				'ScreenTitle': ''
				}

screenStore = valuestore.NewValueStore(paramstore.ParamStore('ScreenParams'))

screenparamuse = {}


def InitScreenParams(parseconfig):
	for p, v in ScreenParams.items():
		screenStore.SetVal(p, type(v)(parseconfig.get(p, v)))


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
				this.userstore.SetVal(p, type(ScreenParams[p])(screensection.get(p, 1)))  # default gets ignored


def AddUndefaultedParams(this, screensection, **kwargs):
	if screensection is None: screensection = {}
	for n, v in kwargs.items():
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
		logsupport.Logs.Log("Button layout error - too many or no buttons: " + butcount, ConsoleError)
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

	def __init__(self, screensection, screenname, parentscreen=None):
		self.userstore = paramstore.ParamStore('Screen-' + screenname,
											   dp=screenStore if parentscreen is None else parentscreen.userstore,
											   locname=screenname)

		self.markradius = int(min(hw.screenwidth, hw.screenheight) * .025)

		self.name = screenname
		self.Active = False  # true if actually on screen
		self.NavKeys = collections.OrderedDict()
		self.Keys = collections.OrderedDict()
		self.WithNav = True
		self.useablevertspace = hw.screenheight - screens.topborder - screens.botborder
		self.initialvertspace = self.useablevertspace
		self.useablehorizspace = hw.screenwidth - 2 * screens.horizborder
		self.startvertspace = screens.topborder
		self.starthorizspace = screens.horizborder
		self.titleoffset = 0
		self.HubInterestList = {}  # one entry per hub, each entry is a dict mapping addr to Node
		self.ScreenTitleBlk = None

		IncorporateParams(self, 'Screen',
						  {'CharColor', 'DimTO', 'PersistTO', 'BackgroundColor', 'CmdKeyCol', 'CmdCharCol',
						   'DefaultHub', 'ScreenTitle', 'ScreenTitleColor', 'ScreenTitleSize'}, screensection)
		AddUndefaultedParams(self, screensection, label=[screenname])

		try:
			self.DefaultHubObj = hubs.hubs.Hubs[self.DefaultHub]
		except KeyError:
			self.DefaultHubObj = None  # todo test what happens later or force this to be an exiting error
			logsupport.Logs.Log("Bad default hub name for screen: ", screenname, severity=ConsoleError)

		if self.ScreenTitle != '':
			# adjust space for a title
			self.ScreenTitleBlk = fonts.fonts.Font(self.ScreenTitleSize, bold=True).render(self.ScreenTitle, 0,
																						   wc(self.ScreenTitleColor))
			h = self.ScreenTitleBlk.get_height()
			w = self.ScreenTitleBlk.get_width()
			titlegap = h // 10  # todo is this the best way to space?
			self.startvertspace = self.startvertspace + h + titlegap
			self.useablevertspace = self.useablevertspace - h - titlegap
			self.titleoffset = screens.horizborder + (self.useablehorizspace - w) // 2

		utilities.register_example('ScreenDesc', self)

	def SetScreenTitle(self, name, fontsz, color):
		if self.ScreenTitleBlk is not None:
			return  # User explicitly set a title so don't override it
		self.ScreenTitleBlk = fonts.fonts.Font(fontsz).render(name, 0, wc(color))
		h = self.ScreenTitleBlk.get_height()
		w = self.ScreenTitleBlk.get_width()
		titlegap = h // 10  # todo is this the best way to space?
		self.startvertspace = self.startvertspace + h + titlegap
		self.useablevertspace = self.useablevertspace - h - titlegap
		self.titleoffset = screens.horizborder + (self.useablehorizspace - w) // 2

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
		debug.debugPrint("Screen", "Base Screen InitDisplay: ", self.name)
		self.PaintBase()
		self.NavKeys = nav
		self.PaintKeys()
		if self.ScreenTitleBlk is not None:
			hw.screen.blit(self.ScreenTitleBlk, (self.titleoffset, screens.topborder))

	def ReInitDisplay(self):
		self.PaintBase()
		self.PaintKeys()
		if self.ScreenTitleBlk is not None:
			hw.screen.blit(self.ScreenTitleBlk, (self.titleoffset, screens.topborder))

	def NodeEvent(self, hub='none', node=9999, value=9999, varinfo=()):
		if node is not None:
			if hub != '*VARSTORE*':  # var changes can be reported while any screen is up
				logsupport.Logs.Log("Unexpected event to screen: ", self.name, ' Hub: ', str(hub), ' Node: ', str(node),
									' Val: ', str(value), severity=ConsoleDetail)
			else:
				pass

	def ExitScreen(self):
		pass

	def PaintBase(self):
		hw.screen.fill(wc(self.BackgroundColor))
		if config.sysStore.ErrorNotice != -1:
			pygame.draw.circle(hw.screen, tint(self.BackgroundColor, tint_factor=.5),
							   (self.markradius, self.markradius), self.markradius, 0)


class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname, parentscreen=None):
		ScreenDesc.__init__(self, screensection, screenname, parentscreen=parentscreen)

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
			hpos.append(screens.horizborder + (.5 + i) * buttonsize[0])
		for i in range(bpc):
			vpos.append(self.startvertspace + extraOffset + (.5 + i) * buttonsize[1])

		for i, (kn, key) in enumerate(self.Keys.items()):
			key.FinishKey((hpos[i % bpr], vpos[i // bpr]), buttonsize)
