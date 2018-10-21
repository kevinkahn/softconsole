import config
import logsupport
from logsupport import ConsoleError, ConsoleWarning
import utilities
import toucharea
import collections
from utilfuncs import wc, tint
import debug
import pygame


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

def ButSize(bpr, bpc, height):
	h = config.screenheight - config.topborder - config.botborder if height == 0 else height
	return (
		(config.screenwidth - 2*config.horizborder)/bpr, h/bpc)



class ScreenDesc(object):
	"""
	Basic information about a screen, subclassed by all other screens to handle this information
	"""

	def __init__(self, screensection, screenname):
		self.CharColor = None
		self.DimTO = 0
		self.PersistTO = 0
		self.BackgroundColor = None
		self.CmdKeyCol = None
		self.CmdCharCol = None
		self.label = None # type: list
		self.DefaultHub = None
		self.markradius = int(min(config.screenwidth, config.screenheight) * .025)

		self.name = screenname
		self.NavKeys = collections.OrderedDict()
		self.Keys = collections.OrderedDict()
		self.WithNav = True
		self.HubInterestList = {} # one entry per hub, each entry is a dict mapping addr to Node

		utilities.LocalizeParams(self, screensection, '-', 'CharColor', 'DimTO', 'PersistTO', 'BackgroundColor',
								 'CmdKeyCol', 'CmdCharCol', label=[screenname],DefaultHub=config.defaulthubname)
		try:
			self.DefaultHub = config.Hubs[self.DefaultHub]
		except KeyError:
			logsupport.Logs.Log("Bad default hub name for screen: ",screenname,severity=ConsoleError)

		utilities.register_example('ScreenDesc', self)

	def PaintKeys(self):
		if self.Keys is not None:
			for key in self.Keys.values():
				if type(key) is not toucharea.TouchPoint:
					key.PaintKey()
		for key in self.NavKeys.values():
			key.PaintKey()

	def AddToHubInterestList(self,hub,item,value):
		if hub.name in self.HubInterestList:
			self.HubInterestList[hub.name][item]=value
		else:
			self.HubInterestList[hub.name] = {item:value}

	def InitDisplay(self, nav):
		debug.debugPrint("Screen", "Base Screen InitDisplay: ", self.name)
		self.PaintBase()
		self.NavKeys = nav
		self.PaintKeys()

	def ReInitDisplay(self):
		self.PaintBase()
		self.PaintKeys()

	def NodeEvent(self, hub='none', node=9999, value=9999, varinfo = ()):
		if node is not None:
			if hub != '*VARSTORE*': # var changes can be reported while any screen is up
				logsupport.Logs.Log("Unexpected event to screen: ", self.name, ' Hub: ', str(hub), ' Node: ', str(node), ' Val: ', str(value),severity = ConsoleWarning)
			else:
				pass

	def ExitScreen(self):
		config.DS.Tasks.RemoveAllGrp(id(self))  # by default delete all pending tasks override if screen needs to

	# keep some tasks going

	def PaintBase(self):
		config.screen.fill(wc(self.BackgroundColor))
		if logsupport.ErrorNotice != -1:
			pygame.draw.circle(config.screen, tint(self.BackgroundColor, tint_factor=.5),
							   (self.markradius, self.markradius), self.markradius, 0)

class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname):
		self.KeysPerColumn = 0
		self.KeysPerRow = 0


		ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeysPerColumn', 'KeysPerRow')

		self.buttonsperrow = -1
		self.buttonspercol = -1
		utilities.register_example('BaseKeyScreenDesc', self)

	def LayoutKeys(self, extraOffset=0, height=0):
		# Compute the positions and sizes for the Keys and store in the Key objects
		explicitlayout = self.KeysPerColumn*self.KeysPerRow

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

		buttonsize = ButSize(bpr, bpc, height)
		hpos = []
		vpos = []
		for i in range(bpr):
			hpos.append(config.horizborder + (.5 + i)*buttonsize[0])
		for i in range(bpc):
			vpos.append(config.topborder + extraOffset + (.5 + i)*buttonsize[1])

		for i, (kn, key) in enumerate(self.Keys.items()):
			key.FinishKey((hpos[i%bpr], vpos[i//bpr]), buttonsize)
