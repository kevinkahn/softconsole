import math

import webcolors

import config
import logsupport
import toucharea
import utilities

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

	def __init__(self, screensection, screenname, ExtraCmdButs=(), withnav=True):
		self.name = screenname
		self.keysbyord = []
		utilities.LocalizeParams(self, screensection, 'CharColor', 'DimTO', 'BackgroundColor', 'CmdKeyCol',
								 'CmdCharCol', label=[screenname])
		self.WithNav = withnav
		self.PrevScreen = self.NextScreen = None
		cbutwidth = (config.screenwidth - 2*config.horizborder)/(2 + len(ExtraCmdButs))
		cvertcenter = config.screenheight - config.botborder/2
		cbutheight = config.botborder - config.cmdvertspace*2
		# todo condition on withnav?  if False then None? if change then also fix FinishScreen not to fail on none
		self.PrevScreenKey = toucharea.ManualKeyDesc('**prev**', ['**prev**'],
													 self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
													 center=(config.horizborder + .5*cbutwidth, cvertcenter),
													 size=(cbutwidth, cbutheight))
		self.NextScreenKey = toucharea.ManualKeyDesc('**next**', ['**next**'],
													 self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
													 center=(
														 config.horizborder + (1 + len(ExtraCmdButs) + .5)*cbutwidth,
														 cvertcenter), size=(cbutwidth, cbutheight))
		self.ExtraCmdKeys = []
		for i in range(len(ExtraCmdButs)):
			hcenter = config.horizborder + (i + 1.5)*cbutwidth
			self.ExtraCmdKeys.append(toucharea.ManualKeyDesc(ExtraCmdButs[i][0], ExtraCmdButs[i][1],
															 self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
															 center=(hcenter, cvertcenter),
															 size=(cbutwidth, cbutheight)))
			self.ExtraCmdKeys[-1].FinishKey((0,0),(0,0))
		utilities.register_example('ScreenDesc', self)

	def FinishScreen(self):
		self.PrevScreenKey.KeyLabelOn = self.PrevScreen.label
		self.NextScreenKey.KeyLabelOn = self.NextScreen.label
		self.PrevScreenKey.FinishKey((0,0),(0,0))
		self.NextScreenKey.FinishKey((0,0),(0,0))

	def PaintBase(self, latetitles=None):
		config.screen.fill(wc(self.BackgroundColor))
		if self.WithNav:
			if not config.DS.BrightenToHome:  # suppress command buttons on sleep screen when any touch witll brighten/gohome
				self.PrevScreenKey.PaintKey()
				self.NextScreenKey.PaintKey()
				i = 0
				for K in self.ExtraCmdKeys:
					K.PaintKey(latetitles[i] if not latetitles is None else None) # todo how to get the new title here?

	def __repr__(self):
		return "ScreenDesc:" + self.name + ":" + self.BackgroundColor + ":" + str(self.DimTO) + ":"


class BaseKeyScreenDesc(ScreenDesc):
	def __init__(self, screensection, screenname, ExtraCmdButs=(), withnav=True):
		ScreenDesc.__init__(self, screensection, screenname, ExtraCmdButs, withnav)
		utilities.LocalizeParams(self, None)
		self.buttonsperrow = -1
		self.buttonspercol = -1
		utilities.register_example('BaseKeyScreenDesc', self)

	def LayoutKeys(self, extraOffset=0, height=0):
		# Compute the positions and sizes for the Keys and store in the Key objects
		bpr, bpc = ButLayout(len(self.keysbyord))
		self.buttonsperrow = bpr
		self.buttonspercol = bpc

		buttonsize = ButSize(bpr, bpc, height)
		hpos = []
		vpos = []
		for i in range(bpr):
			hpos.append(config.horizborder + (.5 + i)*buttonsize[0])
		for i in range(bpc):
			vpos.append(config.topborder + extraOffset + (.5 + i)*buttonsize[1])

		for i in range(len(self.keysbyord)):
			self.keysbyord[i].FinishKey((hpos[i%bpr], vpos[i//bpr]),buttonsize)

	def PaintKeys(self):
		for key in self.keysbyord:
			key.PaintKey()
