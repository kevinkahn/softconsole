import pygame
import inspect

import logsupport
import debug
from screens import screen
import stores.paramstore as paramstore
from utils import timers, utilities, fonts, displayupdate, hw
from utils.hw import scaleW, scaleH
from utils.utilfuncs import wc
import typing
from keys.keyutils import DispOpt, ChooseType, ParseConfigToDispOpt
import stores.valuestore as valuestore
import time


class TouchPoint(object):
	"""
	Represents a touchable rectangle on the screen.
	"""

	def __init__(self, name, Center, Size, proc=None, procdbl=None, proclong=None):
		self.name = name
		self.Size = Size
		self.GappedSize = Size
		self.Center = Center
		self.Screen = None
		self.ControlObj = None
		self.Proc = proc  # function that gets called on touch - expects to take a single parameter which is the type of press
		self.ProcDblTap = procdbl
		self.ProcLong = proclong
		self.Verify = False
		self.AllowSlider = False
		utilities.register_example("TouchPoint", self)

	def ControlObjUndefined(self):
		if self.ControlObj is None: return True
		# noinspection PyBroadException
		try:
			return self.ControlObj.Undefined
		except:
			return False

	def touched(self, pos):
		return (pos[0] > self.Center[0] - self.Size[0] / 2) and (pos[0] < self.Center[0] + self.Size[0] / 2) and \
			   (pos[1] > self.Center[1] - self.Size[1] / 2) and (pos[1] < self.Center[1] + self.Size[1] / 2)

	def Pressed(self, tapcount):
		# print('Pressed: {}({})'.format(self.name, tapcount))
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
		elif tapcount == -1:
			# Long tap
			# print('Long Tap {}'.format(self.ProcLong))
			if self.ProcLong is not None:
				if 'Key' in inspect.signature(self.ProcLong).parameters:
					self.ProcLong(Key=self)
				else:
					self.ProcLong()
			else:
				logsupport.Logs.Log('Key {} got long tap'.format(self.name))
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

	def ConnectandGetNameOverride(self, keyname, keysection):
		return [self.name]

	# noinspection PyMissingConstructor
	def __init__(self, *args, **kwargs):
		self.State = True
		self.UnknownState = False
		self.KeyBlankImage = None  # type: typing.Union[pygame.Surface, None]
		self.KeyUnknownOverlay = None  # type: typing.Union[pygame.Surface, None]
		self.userstore = None
		self.BlinkTimer = None
		self.BlinkState = 0  # 0: not blinking 1: blink on 2: blink off
		self.usekeygaps = True
		self.VerifyScreen = None  # set later by caller if needed
		self.KeyImage = None  # type: typing.Union[pygame.Surface, None]
		self.LastImageValid = False
		self.LastImage = None  # type: typing.Union[pygame.Surface, None]
		self.displayoptions = []
		self.defoption = None
		self.KeyAlpha = None
		if not hasattr(self, 'statebasedkey'): self.statebasedkey = False
		self.builds = 0
		self.timeused = 0

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


		if self.Size[0] != 0:  # this key can be imaged now since it has a size
			self.FinishKey((0, 0), (0, 0))
		utilities.register_example("ManualKeyDesc", self)

	# noinspection PyUnusedLocal
	@staticmethod
	def KeyParameters(label='', bcolor='black', charcoloron='white', charcoloroff='red', center=(0, 0),
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
				   Verify=False, gaps=False, dispopts=(), dispdef=None, var=''):
		# NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
		# because of when config is imported and what walues are at that time versus at call time
		self.userstore = paramstore.ParamStore('Screen-' + thisscreen.name + '-' + keyname, dp=thisscreen.userstore,
											   locname=keyname)
		self.usekeygaps = gaps

		TouchPoint.__init__(self, keyname, center, size, proc=proc, procdbl=procdbl)
		self.Screen = thisscreen
		self.State = State
		self.Screen = thisscreen
		self.Var = var
		screen.IncorporateParams(self, 'TouchArea',
								 {'KeyColor': bcolor,
								  'KeyOffOutlineColor': KOff,
								  'KeyOnOutlineColor': KOn,
								  'KeyCharColorOn': charcoloron, 'KeyCharColorOff': charcoloroff,
								  'KeyColorOn': KCon, 'KeyColorOff': KCoff,
								  'KeyLabelOn': list(KLon), 'KeyLabelOff': list(KLoff)}, {})

		screen.AddUndefaultedParams(self, {}, FastPress=False, Verify=Verify, Blink=Blink, label=label)
		if self.KeyColorOff == '':
			self.KeyColorOff = self.KeyColor
		if self.KeyColorOn == '':
			self.KeyColorOn = self.KeyColor
		self.Proc = proc
		if self.label == ['']:
			try:
				if self.ControlObj.FriendlyName != '':
					self.label = [self.ControlObj.FriendlyName]
			except AttributeError:
				# noinspection PyAttributeOutsideInit
				self.label = [self.name]
		self.displayoptions = dispopts
		if dispdef is None:
			self.defoption = DispOpt(choosertype=ChooseType.Noneval,
									 color=(self.KeyColorOn, self.KeyCharColorOn, self.KeyOnOutlineColor),
									 deflabel=self.label)
		else:
			self.defoption = dispdef

	def dosectioninit(self, thisscreen, keysection, keyname):
		self.userstore = paramstore.ParamStore('Screen-' + thisscreen.name + '-' + keyname, dp=thisscreen.userstore,
											   locname=keyname)
		TouchPoint.__init__(self, keyname, (0, 0), (0, 0))
		screen.IncorporateParams(self, 'TouchArea', {'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
													 'KeyCharColorOn', 'KeyCharColorOff', 'KeyOutlineOffset',
													 'KeyColorOn', 'KeyColorOff',
													 'KeyLabelOn', 'KeyLabelOff'},
								 keysection)  # todo add sliderorientation
		screen.AddUndefaultedParams(self, keysection, FastPress=0, Verify=False, Blink=0, label=[''], Appearance=[],
									DefaultAppearance='',
									Var='')

		try:
			nmoveride = self.ConnectandGetNameOverride(keyname, keysection)
		except Exception as E:
			nmoveride = [self.name]
			print('chk {}'.format(E))
		if self.label == ['']:
			self.label = nmoveride

		if self.KeyColorOff == '':
			self.KeyColorOff = self.KeyColor
		if self.KeyColorOn == '':
			self.KeyColorOn = self.KeyColor
		if self.KeyLabelOn == ['', ]:
			self.KeyLabelOn = self.label
		if self.KeyLabelOff == ['', ]:
			self.KeyLabelOff = self.label

		if self.Appearance:
			for item in self.Appearance:
				self.displayoptions.append(ParseConfigToDispOpt(item, self.label))
		elif self.statebasedkey:
			dull = '/dull' if self.KeyColorOff == self.KeyColorOn else ''
			self.displayoptions.append(DispOpt(choosertype=ChooseType.stateval, chooser='state*on',
											   color=(self.KeyColorOn, self.KeyCharColorOn, self.KeyOnOutlineColor),
											   deflabel=self.KeyLabelOn))
			self.displayoptions.append(DispOpt(choosertype=ChooseType.stateval, chooser='state*off', color=(
			self.KeyColorOff + dull, self.KeyCharColorOff, self.KeyOffOutlineColor), deflabel=self.KeyLabelOff))

		if self.DefaultAppearance == '':
			self.defoption = DispOpt(choosertype=ChooseType.Noneval, color=(self.KeyColorOn,),
									 deflabel=self.label)  # item='None {}'.format(self.KeyColorOn), deflabel=self.label)
		else:
			self.defoption = ParseConfigToDispOpt(self.DefaultAppearance, self.label)

		if self.Verify:
			screen.AddUndefaultedParams(thisscreen, keysection, GoMsg=['Proceed'], NoGoMsg=['Cancel'])
		self.Screen = thisscreen
		self.State = True

	def PaintKey(self):
		start = time.process_time()
		statickey = False
		# for i in self.displayoptions:
		#	print(i)
		# print('Key {}'.format(self.name))
		if hasattr(self, 'Var') and self.Var != '':
			val = valuestore.GetVal(self.Var)

		elif self.statebasedkey:
			if hasattr(self.DisplayObj, 'state'):
				val = self.DisplayObj.state
			else:
				val = self.State  # try to accommodate ISY hub code that uses events to update key state
		else:
			statickey = True
			val = 99999999  # key display is static

		if not self.LastImageValid:
			self.BuildDynKey(val, 0, True)
			if statickey: self.LastImageValid = True

		x = self.Center[0] - self.GappedSize[0] / 2
		y = self.Center[1] - self.GappedSize[1] / 2

		if self.BlinkState == 2:
			hw.screen.blit(self.KeyBlankImage, (x, y))
		else:
			hw.screen.blit(self.KeyImage, (x, y))
		if self.UnknownState:
			# overlay an X for lost states
			hw.screen.blit(self.KeyUnknownOverlay, (x, y))
		self.timeused = self.timeused + time.process_time() - start
		self.builds += 1
		if self.builds > 30:
			print("Ave time for key {} was {}".format(self.name, self.timeused / self.builds))
			self.timeused = 0
			self.builds = 0

	def FlashNo(self, cycle):
		if cycle != 0:
			# use Blink Timer since never blink and flash at same time
			if self.BlinkTimer is not None:  # if there is an existing Blink going end it
				if self.BlinkTimer.is_alive():
					self.BlinkTimer.cancel()
					self.PaintKey()  # force to real state
					displayupdate.updatedisplay()
			self.BlinkTimer = timers.CountedRepeatingPost(.5, cycle, start=True, name=self.name + '-Blink',
														  proc=self._FlashNo)
			self.Screen.ScreenTimers.append((self.BlinkTimer, None))

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
			displayupdate.updatedisplay()  # actually change the display - used to do in PaintKey but that causes redundancy
			self.UnknownState = False  # alsways leave it false since we may never return if screen is left

	def ScheduleBlinkKey(self, cycle):
		if cycle != 0:
			if self.BlinkTimer is not None:  # if there is an existing Blink going end it
				if self.BlinkTimer.is_alive():
					self.BlinkTimer.cancel()
					self.PaintKey()  # force to real state
					self.BlinkState = 0
					displayupdate.updatedisplay()
			self.BlinkTimer = timers.CountedRepeatingPost(.5, cycle, start=True, name=self.name + '-Blink',
														  proc=self.BlinkKey)
			self.Screen.ScreenTimers.append((self.BlinkTimer, self.AbortBlink))

	def AbortBlink(self):
		print('abort')
		self.BlinkState = 0

	def BlinkKey(self, event):
		if self.Screen.Active:
			cycle = event.count
			if cycle > 1:
				if cycle % 2 == 0:
					self.BlinkState = 2
					self.PaintKey()  # force on todo simplify

				else:
					self.BlinkState = 1
					self.PaintKey()  # force off

			else:
				self.BlinkState = 0
				self.PaintKey()  # make sure to leave it in real state

			displayupdate.updatedisplay()  # actually change the display - used to do in PaintKey but that causes redundancy

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

	def SetOnAlpha(self, alpha):
		self.KeyAlpha = alpha

	def InitDisplay(self):
		# called for each key on a screen when it first displays - allows setting initial state for key display
		debug.debugPrint("Screen", "Base Key.InitDisplay ", self.Screen.name, self.name)
		self.BlinkState = 0

	def _BuildKeyImage(self, color, buttonsmaller, outlineclr):
		temp = pygame.Surface(self.GappedSize)
		pygame.draw.rect(temp, color, ((0, 0), self.Size), 0)
		bord = self.KeyOutlineOffset
		pygame.draw.rect(temp, wc(outlineclr), ((scaleW(bord), scaleH(bord)), buttonsmaller), bord)
		return temp

	def BuildDynKey(self, val, firstfont, shrink):

		def parsecolor(cname):
			cd = 0.0 if len(cname.split('/')) == 1 else 0.5 if cname.split('/')[1] == 'dull' else float(
				cname.split('/')[1])
			return wc(cname.split('/')[0], factor=cd)

		if self.defoption is None:
			lab = 'missing'
		else:
			lab = self.defoption.Label[:]

		color = parsecolor(self.defoption.Color[0])
		chcolor = parsecolor(self.defoption.Color[1] if len(self.defoption.Color) > 1 else self.KeyCharColorOn)
		outlncolor = parsecolor(self.defoption.Color[2] if len(self.defoption.Color) > 2 else self.KeyOnOutlineColor)
		for i in self.displayoptions:
			if i.Matches(val):
				lab = i.Label[:]
				color = parsecolor(i.Color[0])
				chcolor = parsecolor(i.Color[1] if len(i.Color) > 1 else self.KeyColorOn)
				outlncolor = parsecolor(i.Color[2] if len(i.Color) > 2 else self.KeyOnOutlineColor)
				break
		lab2 = []
		dval = '--' if val is None else str(val)
		for line in lab:
			lab2.append(line.replace('$', dval))

		if self.usekeygaps:
			self.GappedSize = (self.Size[0] - self.Screen.HorizButGap, self.Size[1] - self.Screen.VertButGap)
		else:
			self.GappedSize = self.Size

		buttonsmaller = (self.GappedSize[0] - scaleW(6), self.GappedSize[1] - scaleH(6))

		# create image of key
		self.KeyImage = self._BuildKeyImage(color, buttonsmaller, outlncolor)
		self.KeyBlankImage = self._BuildKeyImage(wc(self.Screen.BackgroundColor), buttonsmaller,
												 wc(outlncolor))  # self.Screen.BackgroundColor))

		self.KeyUnknownOverlay = pygame.Surface(self.GappedSize)
		pygame.draw.line(self.KeyUnknownOverlay, wc(self.KeyCharColorOn), (0, 0), self.GappedSize,
						 self.KeyOutlineOffset)
		pygame.draw.line(self.KeyUnknownOverlay, wc(self.KeyCharColorOn), (0, self.GappedSize[1]),
						 (self.GappedSize[0], 0), self.KeyOutlineOffset)
		self.KeyUnknownOverlay.set_alpha(128)

		fontchoice = self.FindFontSize(lab2, firstfont, shrink)
		self.AddTitle(self.KeyImage, lab2, fontchoice, chcolor)

		if self.KeyAlpha is not None:
			self.KeyImage.set_alpha(self.KeyAlpha)

	# noinspection PyAttributeOutsideInit
	def FinishKey(self, center, size, firstfont=0, shrink=True):
		if size[
			0] != 0:  # if size is not zero then set the pos/size of the key; otherwise it was previously set in manual creation
			self.Center = center
			self.Size = size

		if self.KeyLabelOn == ['', ]:
			self.KeyLabelOn = self.label
		if self.KeyLabelOff == ['', ]:
			self.KeyLabelOff = self.label

