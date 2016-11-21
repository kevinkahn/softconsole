import math

import webcolors

import config
import logsupport
import utilities
import toucharea
import collections

wc = webcolors.name_to_rgb


def FlatenScreenLabel(label):
	scrlabel = label[0]
	for s in label[1:]:
		scrlabel = scrlabel + " " + s
	return scrlabel


def ButLayout(butcount):
	butbreaks = (5, 8, 12, 16)
	try:
		q = next(t[0] for t in enumerate([float(y)/butcount for y in butbreaks]) if t[1] >= 1)
		return q + 1, int(math.ceil(float(butcount)/(q + 1)))
	except (ZeroDivisionError, StopIteration):
		config.Logs.Log("Button layout error - too many or no buttons", logsupport.ConsoleError)
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

	def EnterScreen(self):
		config.Logs.Log("EnterScreen not defined: ", self.name, severity=logsupport.ConsoleError)

	def InitDisplay(self, nav):
		self.PaintBase()
		self.NavKeys = nav
		self.PaintKeys()

	def ReInitDisplay(self):
		self.PaintBase()
		self.PaintKeys()

	def ISYEvent(self, node, value):
		config.Logs.Log("Unexpected ISY event to screen: ", self.name, severity=logsupport.ConsoleWarning)

	def ExitScreen(self):
		config.DS.Tasks.RemoveAllScreen(id(self))  # by default delete all pending tasks override if screen needs to

	# keep some tasks going

	def PaintBase(self):
		config.screen.fill(wc(self.BackgroundColor))


class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname):
		ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, None, '')
		self.buttonsperrow = -1
		self.buttonspercol = -1
		utilities.register_example('BaseKeyScreenDesc', self)

	def LayoutKeys(self, extraOffset=0, height=0):
		# Compute the positions and sizes for the Keys and store in the Key objects
		bpr, bpc = ButLayout(len(self.Keys))
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
