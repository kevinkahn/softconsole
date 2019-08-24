import pygame
import inspect

import logsupport
import debug
import fonts
import hw
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

	def __init__(self, name, Center, Size, proc=None, procdbl=None):
		self.name = name
		self.Size = Size
		self.GappedSize = Size
		self.Center = Center
		self.Screen = None
		self.ControlObj = None
		self.Proc = proc  # function that gets called on touch - expects to take a single parameter which is thee type of press
		self.ProcDblTap = procdbl
		self.Verify = False
		utilities.register_example("TouchPoint", self)

	def ControlObjUndefined(self):
		if self.ControlObj is None: return True
		try:
			return self.ControlObj.Undefined
		except:
			return False

	def touched(self, pos):
		return (pos[0] > self.Center[0] - self.Size[0] / 2) and (pos[0] < self.Center[0] + self.Size[0] / 2) and \
			   (pos[1] > self.Center[1] - self.Size[1] / 2) and (pos[1] < self.Center[1] + self.Size[1] / 2)

	def Pressed(self, tapcount):
		if tapcount == 1:
			if self.Proc is not None:
				if 'Key' in inspect.signature(self.Proc).parameters:
					self.Proc(Key=self)
				else:
					self.Proc()
		elif tapcount == 2:
			if self.ProcDblTap is not None:
				if 'Key' in inspect.signature(self.ProcDblTap).parameters:
					self.ProcDblTap(Key=self)
				else:
					self.ProcDblTap()
		else:
			logsupport.Logs.Log('Toucharea got wrong press count {}'.format(tapcount),
								severity=logsupport.ConsoleWarning)

	def HandleNodeEvent(self, evnt):
		logsupport.Logs.Log('Node event to key without handler: Key: {} Event: {}'.format(self.name, evnt),
							severity=logsupport.ConsoleWarning)


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
		self.autocolordull = True
		self.usekeygaps = True

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

		self.autocolordull = self.KeyColorOff == ''
		if self.KeyColorOff == '':
			self.KeyColorOff = self.KeyColor
		if self.KeyColorOn == '':
			self.KeyColorOn = self.KeyColor
		if self.Size[0] != 0:  # this key can be imaged now since it has a size
			self.FinishKey((0, 0), (0, 0))
		utilities.register_example("ManualKeyDesc", self)

	# noinspection PyUnusedLocal
	def KeyParameters(self, label='', bcolor='black', charcoloron='white', charcoloroff='red', center=(0, 0),
					  size=(0, 0),
					  KOn=None, KOff=None, proc=None, procdbl=None, KCon='', KCoff='', KLon=('',), KLoff=('',),
					  State=True, Blink=0, Verify=False):
		# turn this into a dict that matches the section options
		D = {'KeyColor': bcolor, 'KeyOffOutlineColor': KOff, 'KeyOnOutlineColor': KOn,
			 'KeyCharColorOn': charcoloron, 'KeyCharColorOff': charcoloroff,
			 'KeyColorOn': KCon, 'KeyColorOff': KCoff,
			 'KeyLabelOn': list(KLon), 'KeyLabelOff': list(KLoff)}

	def docodeinit(self, thisscreen, keyname, label, bcolor, charcoloron, charcoloroff, center=(0, 0), size=(0, 0),
				   KOn=None,
				   KOff=None, proc=None, procdbl=None, KCon='', KCoff='', KLon=('',), KLoff=('',), State=True, Blink=0,
				   Verify=False, gaps=False):
		# NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
		# because of when config is imported and what walues are at that time versus at call time
		self.userstore = paramstore.ParamStore('Screen-' + thisscreen.name + '-' + keyname, dp=thisscreen.userstore,
											   locname=keyname)
		self.usekeygaps = gaps

		TouchPoint.__init__(self, keyname, center, size, proc=proc, procdbl=procdbl)
		self.Screen = thisscreen
		self.State = State
		self.Screen = thisscreen
		self.VerifyScreen = None  # set later by caller if needed
		screen.IncorporateParams(self, 'TouchArea',
								 {'KeyColor': bcolor,
								  'KeyOffOutlineColor': KOff,
								  'KeyOnOutlineColor': KOn,
								  'KeyCharColorOn': charcoloron, 'KeyCharColorOff': charcoloroff,
								  'KeyColorOn': KCon, 'KeyColorOff': KCoff,
								  'KeyLabelOn': list(KLon), 'KeyLabelOff': list(KLoff)}, {})

		screen.AddUndefaultedParams(self, {}, FastPress=False, Verify=Verify, Blink=Blink, label=label)
		self.Proc = proc

	def InsertVerify(self, scrn):
		self.VerifyScreen = scrn
		self.Proc = self.VerifyScreen.Invoke


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
		x = self.Center[0] - self.GappedSize[0] / 2
		y = self.Center[1] - self.GappedSize[1] / 2
		if not ForceDisplay:
			DisplayState = self.State
		# ignore Key state and display as "DisplayState"
		if DisplayState:
			hw.screen.blit(self.KeyOnImage, (x, y))
		else:
			hw.screen.blit(self.KeyOffImage, (x, y))
		if self.UnknownState:
			# overlay an X for lost states
			hw.screen.blit(self.KeyUnknownOverlay, (x, y))

	def FlashNo(self, cycle):
		if cycle != 0:
			# use Blink Timer since never blink and flash at same time
			if self.BlinkTimer is not None:  # if there is an existing Blink going end it
				if self.BlinkTimer.is_alive():
					self.BlinkTimer.cancel()
					self.PaintKey()  # force to real state
					pygame.display.update()
			self.BlinkTimer = timers.CountedRepeatingPost(.5, cycle, start=True, name=self.name + '-Blink',
														  proc=self._FlashNo)
			self.Screen.ScreenTimers.append(self.BlinkTimer)

	def _FlashNo(self, event):
		if self.Screen.Active:
			cycle = event.count
			if cycle > 1:
				if cycle % 2 == 0:
					self.UnknownState = True
					self.PaintKey()
				else:
					self.PaintKey()
			else:
				self.UnknownState = False
				self.PaintKey()  # make sure to leave it in real state
			pygame.display.update()  # actually change the display - used to do in PaintKey but that causes redundancy
			self.UnknownState = False  # alsways leave it false since we may never return if screen is left

	def ScheduleBlinkKey(self, cycle):
		if cycle != 0:
			if self.BlinkTimer is not None: # if there is an existing Blink going end it
				if self.BlinkTimer.is_alive():
					self.BlinkTimer.cancel()
					self.PaintKey() # force to real state
					pygame.display.update()
			self.BlinkTimer = timers.CountedRepeatingPost(.5, cycle, start=True, name=self.name + '-Blink', proc=self.BlinkKey)
			self.Screen.ScreenTimers.append(self.BlinkTimer)

	def BlinkKey(self, event):
		if self.Screen.Active:
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
			vert_off = ((i + 1) * self.GappedSize[1] / (1 + lines)) - ren.get_height() / 2
			horiz_off = (self.GappedSize[0] - ren.get_width()) / 2
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
		if self.usekeygaps:
			self.GappedSize = (self.Size[0] - self.Screen.HorizButGap, self.Size[1] - self.Screen.VertButGap)
		else:
			self.GappedSize = self.Size

		buttonsmaller = (self.GappedSize[0] - scaleW(6), self.GappedSize[1] - scaleH(6))


		# create image of ON key
		self.KeyOnImageBase = pygame.Surface(self.GappedSize)
		pygame.draw.rect(self.KeyOnImageBase, coloron, ((0, 0), self.Size), 0)
		bord = self.KeyOutlineOffset
		pygame.draw.rect(self.KeyOnImageBase, wc(self.KeyOnOutlineColor), ((scaleW(bord), scaleH(bord)), buttonsmaller),
						 bord)

		# create image of OFF key
		self.KeyOffImageBase = pygame.Surface(self.GappedSize)
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
		if self.autocolordull:
			s = pygame.Surface(self.Size)
			s.set_alpha(150)
			s.fill(wc("white"))
			self.KeyOffImageBase.blit(s, (0, 0))

		# Add the labels
		self.SetKeyImages(self.KeyLabelOn, self.KeyLabelOff, firstfont, shrink)
