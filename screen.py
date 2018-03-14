import config
import logsupport
import utilities
import toucharea
import collections
from utilities import wc
from debug import debugPrint


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
		logsupport.Logs.Log("Button layout error - too many or no buttons: " + butcount, logsupport.ConsoleError)
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
		self.name = screenname
		self.NavKeys = collections.OrderedDict()
		self.Keys = collections.OrderedDict()
		self.WithNav = True
		self.NodeList = {}
		self.VarsList = {}

		utilities.LocalizeParams(self, screensection, '-', 'CharColor', 'DimTO', 'PersistTO', 'BackgroundColor',
								 'CmdKeyCol',
								 'CmdCharCol', 'DimLevel', 'BrightLevel', label=[screenname])
		self.Subscreens = {}  # support easy switching to subscreens - name:subscreen

		utilities.register_example('ScreenDesc', self)

	def PaintKeys(self):
		for key in self.Keys.itervalues():
			if type(key) is not toucharea.TouchPoint:
				key.PaintKey()
		for key in self.NavKeys.itervalues():
			key.PaintKey()


	def InitDisplay(self, nav):
		debugPrint("Screen", "Base Screen InitDisplay: ", self.name)
		self.PaintBase()
		self.NavKeys = nav
		self.PaintKeys()

	def ReInitDisplay(self):
		self.PaintBase()
		self.PaintKeys()

	def ISYEvent(self, node, value):
		logsupport.Logs.Log("Unexpected ISY event to screen: ", self.name, severity=logsupport.ConsoleWarning)

	def ExitScreen(self):
		config.DS.Tasks.RemoveAllGrp(id(self))  # by default delete all pending tasks override if screen needs to

	# keep some tasks going

	def PaintBase(self):
		config.screen.fill(wc(self.BackgroundColor))


class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname):
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
				logsupport.Logs.Log('Bad explicit key layout for: ', self.name, severity=logsupport.ConsoleWarning)
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

		for i, (kn, key) in enumerate(self.Keys.iteritems()):
			key.FinishKey((hpos[i%bpr], vpos[i//bpr]), buttonsize)
