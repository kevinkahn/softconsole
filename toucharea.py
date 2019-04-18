import pygame

import config
import debug
import fonts
import screen
import stores.paramstore as paramstore
import timers
import utilities
from hw import scaleW, scaleH
from utilfuncs import wc


class TouchPoint(object):
	"""
	Represents a touchable rectangle on the screen.
	"""

	def __init__(self, name, Center, Size, proc=None):
		self.name = name
		self.Size = Size
		self.Center = Center
		self.Screen = None
		self.ControlObj = None
		self.Proc = proc  # function that gets called on touch - expects to take a single parameter which is thee type of press

		utilities.register_example("TouchPoint", self)

	def touched(self, pos):
		return (pos[0] > self.Center[0] - self.Size[0] / 2) and (pos[0] < self.Center[0] + self.Size[0] / 2) and \
			   (pos[1] > self.Center[1] - self.Size[1] / 2) and (pos[1] < self.Center[1] + self.Size[1] / 2)


class ManualKeyDesc(TouchPoint):
	"""
	Defines a drawn touchable rectangle on the screen that represents a key (button).  May be called with one of 2
	signatures.  It can be called manually by code to create a key by supplying all the attributes of the key in the
	code explicitly.  It can also be called with a config objects section in which case it will build the key from the
	combination of the defaults for the attributes and the explicit overides found in the config.txt file section
	that is passed in.
	"""

	def __setattr__(self, key, value):
		if key not in screen.ScreenParams:
			object.__setattr__(self, key, value)
		else:
			self.userstore.SetVal(key, value)

	# object.__setattr__(self, key, value)

	def __getattr__(self, key):
		return self.userstore.GetVal(key)

	# noinspection PyMissingConstructor
	def __init__(self, *args, **kwargs):
		self.State = True
		self.UnknownState = False
		self.KeyOnImage = None  # type: pygame.Surface
		self.KeyOffImage = None  # type: pygame.Surface
		self.KeyOnImageBase = None  # type: pygame.Surface
		self.KeyOffImageBase = None  # type: pygame.Surface
		self.KeyUnknownOverlay = None  # type: pygame.Surface
		self.userstore = None
		self.BlinkTimer = None

		# alternate creation signatures
		self.ButtonFontSizes = (31, 28, 25, 22, 20, 18, 16)
		if len(args) == 3:
			# signature: ManualKeyDesc(screen, keysection, keyname)
			# initialize by reading config file
			self.dosectioninit(*args)
		else:
			# signature: ManualKeyDesc(screen, keyname, label, bcolor, charcoloron, charcoloroff, center=, size=, KOn=, KOff=, proc=)
			# initializing from program code case
			self.docodeinit(*args, **kwargs)
		# Future may need to change signature if handling "holds"?
		if self.KeyColorOff == '':
			self.KeyColorOff = self.KeyColor
		if self.KeyColorOn == '':
			self.KeyColorOn = self.KeyColor
		if self.Size[0] != 0:  # this key can be imaged now since it has a size
			self.FinishKey((0, 0), (0, 0))
		utilities.register_example("ManualKeyDesc", self)

	# noinspection PyUnusedLocal
	def docodeinit(self, thisscreen, keyname, label, bcolor, charcoloron, charcoloroff, center=(0, 0), size=(0, 0),
				   KOn=None,
				   KOff=None, proc=None, KCon='', KCoff='', KLon=('',), KLoff=('',), State=True, Blink=0, Verify=False):
		# NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
		# because of when config is imported and what walues are at that time versus at call time
		self.userstore = paramstore.ParamStore('Screen-' + thisscreen.name + '-' + keyname, dp=thisscreen.userstore,
											   locname=keyname)

		TouchPoint.__init__(self, keyname, center, size, proc=proc)
		self.Screen = thisscreen
		self.State = State
		self.Screen = thisscreen
		screen.IncorporateParams(self, 'TouchArea',
								 {'KeyColor': bcolor,
								  'KeyOffOutlineColor': KOff,
								  'KeyOnOutlineColor': KOn,
								  'KeyCharColorOn': charcoloron, 'KeyCharColorOff': charcoloroff,
								  'KeyColorOn': KCon, 'KeyColorOff': KCoff,
								  'KeyLabelOn': list(KLon), 'KeyLabelOff': list(KLoff)}, {})

		screen.AddUndefaultedParams(self, {}, FastPress=False, Verify=False, Blink=Blink, label=label)

	def dosectioninit(self, thisscreen, keysection, keyname):
		self.userstore = paramstore.ParamStore('Screen-' + thisscreen.name + '-' + keyname, dp=thisscreen.userstore,
											   locname=keyname)
		TouchPoint.__init__(self, keyname, (0, 0), (0, 0))
		screen.IncorporateParams(self, 'TouchArea', {'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
													 'KeyCharColorOn', 'KeyCharColorOff', 'KeyOutlineOffset',
													 'KeyColorOn', 'KeyColorOff',
													 'KeyLabelOn', 'KeyLabelOff'}, keysection)
		screen.AddUndefaultedParams(self, keysection, FastPress=0, Verify=False, Blink=0, label=[''])

		if self.Verify:
			screen.AddUndefaultedParams(thisscreen, keysection, GoMsg=['Proceed'], NoGoMsg=['Cancel'])
		self.Screen = thisscreen
		self.State = True

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		x = self.Center[0] - self.Size[0] / 2
		y = self.Center[1] - self.Size[1] / 2
		if not ForceDisplay:
			DisplayState = self.State
		# ignore Key state and display as "DisplayState"
		if DisplayState:
			config.screen.blit(self.KeyOnImage, (x, y))
		else:
			config.screen.blit(self.KeyOffImage, (x, y))
		if self.UnknownState:
			# overlay an X for lost states
			config.screen.blit(self.KeyUnknownOverlay, (x, y))

	def ScheduleBlinkKey(self, cycle):
		if cycle != 0:
			if self.BlinkTimer is not None: # if there is an existing Blink going end it
				if self.BlinkTimer.is_alive():
					self.BlinkTimer.cancel()
					self.PaintKey() # force to real state
					pygame.display.update()
			self.BlinkTimer = timers.CountedRepeatingPost(.5, cycle, start=True, name=self.name + '-Blink', proc=self.BlinkKey)

	def BlinkKey(self, event):
		cycle = event.count
		if cycle > 1:
			if cycle % 2 == 0:
				self.PaintKey(ForceDisplay=True, DisplayState=True)  # force on
			else:
				self.PaintKey(ForceDisplay=True, DisplayState=False)  # force off
		else:
			self.PaintKey()  # make sure to leave it in real state
		pygame.display.update()  # actually change the display - used to do in PaintKey but that causes redundancy

	def FindFontSize(self, lab, firstfont, shrink):
		lines = len(lab)
		buttonsmaller = (self.Size[0] - scaleW(6), self.Size[1] - scaleH(6))
		# compute writeable area for text
		textarea = (buttonsmaller[0] - 2, buttonsmaller[1] - 2)
		fontchoice = self.ButtonFontSizes[firstfont]
		if shrink:
			for l in range(lines):
				for i in range(firstfont, len(self.ButtonFontSizes) - 1):
					txtsize = fonts.fonts.Font(self.ButtonFontSizes[i], bold=True).size(lab[l])
					if lines * txtsize[1] >= textarea[1] or txtsize[0] >= textarea[0]:
						fontchoice = self.ButtonFontSizes[i + 1]
		return fontchoice

	def AddTitle(self, surface, label, fontchoice, color):
		lines = len(label)
		for i in range(lines):
			ren = fonts.fonts.Font(fontchoice, bold=True).render(label[i], 0, wc(color))
			vert_off = ((i + 1) * self.Size[1] / (1 + lines)) - ren.get_height() / 2
			horiz_off = (self.Size[0] - ren.get_width()) / 2
			surface.blit(ren, (horiz_off, vert_off))

	def SetKeyImages(self, onLabel, offLabel=None, firstfont=0, shrink=True):
		if offLabel is None:
			offLabel = onLabel
		self.KeyOnImage = self.KeyOnImageBase.copy()
		self.KeyOffImage = self.KeyOffImageBase.copy()
		fontchoice = self.FindFontSize(onLabel, firstfont, shrink)
		self.AddTitle(self.KeyOnImage, onLabel, fontchoice, self.KeyCharColorOn)
		fontchoice = self.FindFontSize(offLabel, firstfont, shrink)
		self.AddTitle(self.KeyOffImage, offLabel, fontchoice, self.KeyCharColorOff)

	def InitDisplay(self):
		# called for each key on a screen when it first displays - allows setting initial state for key display
		debug.debugPrint("Screen", "Base Key.InitDisplay ", self.Screen.name, self.name)

	def BuildKey(self, coloron, coloroff):
		buttonsmaller = (self.Size[0] - scaleW(6), self.Size[1] - scaleH(6))

		# create image of ON key
		self.KeyOnImageBase = pygame.Surface(self.Size)
		pygame.draw.rect(self.KeyOnImageBase, coloron, ((0, 0), self.Size), 0)
		bord = self.KeyOutlineOffset
		pygame.draw.rect(self.KeyOnImageBase, wc(self.KeyOnOutlineColor), ((scaleW(bord), scaleH(bord)), buttonsmaller),
						 bord)

		# create image of OFF key
		self.KeyOffImageBase = pygame.Surface(self.Size)
		pygame.draw.rect(self.KeyOffImageBase, coloroff, ((0, 0), self.Size), 0)
		bord = self.KeyOutlineOffset
		pygame.draw.rect(self.KeyOffImageBase, wc(self.KeyOffOutlineColor),
						 ((scaleW(bord), scaleH(bord)), buttonsmaller), bord)

		self.KeyUnknownOverlay = pygame.Surface(self.Size)
		pygame.draw.line(self.KeyUnknownOverlay, wc(self.KeyCharColorOn), (0, 0), self.Size, bord)
		pygame.draw.line(self.KeyUnknownOverlay, wc(self.KeyCharColorOn), (0, self.Size[1]), (self.Size[0], 0), bord)
		self.KeyUnknownOverlay.set_alpha(128)

	# noinspection PyAttributeOutsideInit
	def FinishKey(self, center, size, firstfont=0, shrink=True):
		if size[
			0] != 0:  # if size is not zero then set the pos/size of the key; otherwise it was previously set in manual creation
			self.Center = center
			self.Size = size
		if self.label == ['']:
			try:
				if self.ControlObj.FriendlyName != '':
					self.label = [self.ControlObj.FriendlyName]
			except AttributeError:
				# noinspection PyAttributeOutsideInit
				self.label = [self.name]
		if self.KeyLabelOn == ['', ]:
			self.KeyLabelOn = self.label
		if self.KeyLabelOff == ['', ]:
			self.KeyLabelOff = self.label

		self.BuildKey(wc(self.KeyColorOn), wc(self.KeyColorOff))

		# dull the OFF key
		s = pygame.Surface(self.Size)
		s.set_alpha(150)
		s.fill(wc("white"))
		self.KeyOffImageBase.blit(s, (0, 0))

		# Add the labels
		self.SetKeyImages(self.KeyLabelOn, self.KeyLabelOff, firstfont, shrink)
