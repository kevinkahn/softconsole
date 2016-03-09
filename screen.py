import math

import webcolors

import config
import logsupport
import toucharea
import utilities

wc = webcolors.name_to_rgb


def FlatenScreenLabel(label):
	scrlabel = ""
	for s in label:
		scrlabel = scrlabel + " " + s
	return scrlabel


def ButLayout(butcount):
	butbreaks = (5, 8, 12, 16)
	try:
		q = next(t[0] for t in enumerate([float(y)/butcount for y in butbreaks]) if t[1] >= 1)
		return q + 1, int(math.ceil(float(butcount)/(q + 1)))
	except (ZeroDivisionError, StopIteration):
		config.Logs.Log("Button layout error - too many or no buttons", logsupport.Error)
		return 5, 5



def ButSize(bpr, bpc, height):
	h = config.screenheight - config.topborder - config.botborder if height == 0 else height
	return (
		(config.screenwidth - 2*config.horizborder)/bpr, h/bpc)


class ScreenDesc(object):
	"""
	Basic information about a screen, subclassed by all other screens to handle this information
	"""

	def SetExtraCmdTitles(self, titles):
		for i in range(len(titles)):
			self.ExtraCmdKeys[i].label = titles[i]

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
		# todo condition on withnav?  if False then None?
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
			self.ExtraCmdKeys.append(toucharea.ManualKeyDesc(ExtraCmdButs[i], ExtraCmdButs[i],
															 self.CmdKeyCol, self.CmdCharCol, self.CmdCharCol,
															 center=(hcenter, cvertcenter),
															 size=(cbutwidth, cbutheight)))
		utilities.register_example('ScreenDesc', self)

	def FinishScreen(self):  # todo this makes no sense since I set PrevScreen in init above
		if self.PrevScreen is None:
			self.PrevScreenKey = None
		else:
			self.PrevScreenKey.label = self.PrevScreen.label
			self.NextScreenKey.label = self.NextScreen.label

	def PaintBase(self):
		config.screen.fill(wc(self.BackgroundColor))
		if self.WithNav:
			config.DS.draw_cmd_buttons(self)

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

		for i in range(len(self.keysbyord)): #todo this should call finish key
			K = self.keysbyord[i]
			K.Center = (hpos[i%bpr], vpos[i//bpr])
			K.Size = buttonsize

	def PaintKeys(self):
		for key in self.keysbyord:
			config.DS.draw_button(key) # todo this should call paint key
