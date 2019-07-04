import functools

import pygame
from pygame import draw

import debug
import fonts
import hw
import logsupport
import screen
import screens.__screens as screens
import screenutil
import toucharea
import utilities
from logsupport import ConsoleDetail
from toucharea import TouchPoint, ManualKeyDesc
from utilfuncs import wc


class VerifyScreen(screen.BaseKeyScreenDesc):

	def __init__(self, key, gomsg, nogomsg, procyes, procno, callingscreen, bcolor, keycoloroff, charcolor, state,
				 interestlist):
		screen.BaseKeyScreenDesc.__init__(self, {}, key.name + '-Verify', parentscreen=key)
		debug.debugPrint('Screen', "Build Verify Screen")
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.HubInterestList = interestlist
		self.DimTO = 20
		self.PersistTO = 10
		self.label = screen.FlatenScreenLabel(key.label)
		self.ClearScreenTitle()  # don't use parent screen title
		self.CallingScreen = callingscreen
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.SetScreenTitle(self.label, 40, charcolor)
		self.Keys['yes'] = ManualKeyDesc(self, 'yes', gomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['yes'].Proc = procyes  # functools.partial(proc, True)
		self.Keys['no'] = ManualKeyDesc(self, 'no', nogomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['no'].Proc = procno if procno is not None else self.DefaultNo  # functools.partial(proc, False)

		self.LayoutKeys(self.startvertspace, self.useablevertspace)
		utilities.register_example("VerifyScreen", self)

	@staticmethod
	def DefaultNo():
		screens.DS.SwitchScreen(screen.BACKTOKEN, 'Bright', 'Verify denied')

	def Invoke(self):
		screens.DS.SwitchScreen(self, 'Bright', 'Do Verify ' + self.name, push=True)

	def ShowScreen(self):
		self.ReInitDisplay()
		self.PaintKeys()
		pygame.display.update()

	def InitDisplay(self, nav):
		# debugPrint('Main', "Enter to screen: ", self.name)
		logsupport.Logs.Log('Entering Verify Screen: ' + self.name, severity=ConsoleDetail)
		super(VerifyScreen, self).InitDisplay({})
		self.ShowScreen()


class ValueChangeScreen(screen.ScreenDesc):  # todo may need to call super class
	# need to set no nav keys
	@staticmethod
	def offsetpoint(center, point):
		return center[0] + point[0], center[1] + point[1]

	def CancelChange(self):
		pass

	def AcceptChange(self):
		pass

	def ValChange(self, delta):
		pass

	# noinspection PyMissingConstructor
	def __init__(self, BackgroundColor, Outline, CharColor, label, initvalue, changevals, setvalueproc, returnscreen):
		screen.ScreenDesc.__init__(self, {}, label + ' -ValChange')
		self.BackgroundColor = BackgroundColor
		self.Outline = Outline
		self.CharColor = CharColor
		self.label = label
		self.initvalue = initvalue
		self.changevals = changevals
		self.setvalueproc = setvalueproc
		self.returnscreen = returnscreen

		self.name = "VALUECHANGESCREEN"
		self.Value = initvalue
		self.Keys = {}
		vertzonepct = .8
		vertzonesize = int(.25 * hw.screenheight)  # todo switch to use useable vert hgt
		screencenter = (hw.screenwidth / 2, hw.screenheight / 2)  # todo switch to use useable vert hgt

		self.font = fonts.fonts.Font(40)

		self.arrowht = int(vertzonesize * vertzonepct)
		self.arrowwd = min(.8 * (hw.screenwidth / len(changevals)), self.arrowht)
		self.uparrowcenter = []
		self.dnarrowcenter = []
		self.uparrowverts = []
		self.dnarrowverts = []
		self.uparrow = [[0, self.arrowht / 2], [self.arrowwd / 2, -self.arrowht / 2],
						[-self.arrowwd / 2, -self.arrowht / 2]]  # verticies ref 0,0 center
		self.dnarrow = [[0, -self.arrowht / 2], [self.arrowwd / 2, self.arrowht / 2],
						[-self.arrowwd / 2, self.arrowht / 2]]
		self.chgval = []

		for i in range(len(changevals)):
			self.uparrowcenter.append(
				((i + .5) * hw.screenwidth / (len(changevals)), screencenter[1] + vertzonesize))
			self.Keys['up' + str(i)] = TouchPoint('up' + str(i), self.uparrowcenter[
				-1], self.arrowwd, functools.partial(self.ValChange, changevals[i]))
			self.uparrowverts.append(
				[functools.partial(self.offsetpoint, self.uparrowcenter[-1])(self.uparrow[k]) for k in range(3)])
			self.dnarrowcenter.append(
				((i + .5) * hw.screenwidth / (len(changevals)), screencenter[1] - vertzonesize))
			self.Keys['dn' + str(i)] = TouchPoint('up' + str(i), self.dnarrowcenter[
				-1], self.arrowwd, functools.partial(self.ValChange, -changevals[i]))
			self.dnarrowverts.append(
				[functools.partial(self.offsetpoint, self.dnarrowcenter[-1])(self.dnarrow[k]) for k in range(3)])
			fs = self.font.size(str(changevals[i]))
			self.chgval.append(
				((-fs[0] / 2, fs[1]), self.font.render(str(changevals[i]), True, wc(CharColor))))

		self.titlecenter = (screencenter[0] - int(1.75 * vertzonesize), screencenter[1])
		valuebuttoncenter = screencenter
		valuebuttonsize = (hw.screenwidth / 2, int(vertzonesize * vertzonepct))
		labelcenter = (screencenter[0], screencenter[1] - int(1.75 * vertzonesize))
		self.labelrend = self.font.render(label, True, wc(CharColor))
		labelsz = self.font.size(label)
		self.labelloc = (labelcenter[0] - labelsz[0] / 2, labelcenter[1] - labelsz[1] / 2)

		cancelcenter = (screencenter[0], screencenter[1] + int(1.75 * vertzonesize))
		cancelsize = (
		hw.screenwidth / 2, int(vertzonepct * hw.screenheight * .125))  # todo switch to use useable vert hgt

		self.Keys['cancel'] = ManualKeyDesc(self, 'cancel', ['Cancel', ], BackgroundColor, CharColor, CharColor,
											cancelcenter,
											cancelsize, proc=self.CancelChange)
		self.Keys['accept'] = ManualKeyDesc(self, 'accept', ["Accept", "#"], BackgroundColor, CharColor, CharColor,
											valuebuttoncenter,
											valuebuttonsize, proc=self.AcceptChange)
		# need to insert current value (actually in PaintKey probably
		pass

	def InitDisplay(self, nav):
		super(ValueChangeScreen, self).InitDisplay({})  # why do we pass in the nav keys here?

		self.ReInitDisplay()
		# self.PaintBase()
		# write the title with name of var? maybe button should be "accept"
		for i in range(len(self.changevals)):
			fho = self.chgval[i][0][0]
			fvo = self.chgval[i][0][1]
			hw.screen.blit(self.chgval[i][1],
						   self.offsetpoint(self.uparrowcenter[i], (fho, -self.arrowht / 2 + self.arrowht / 10)))
			hw.screen.blit(self.chgval[i][1],
						   self.offsetpoint(self.dnarrowcenter[i],
												(fho, self.arrowht / 2 - fvo - self.arrowht / 10)))
			draw.lines(hw.screen, wc(self.Outline), True, self.uparrowverts[i], 5)
			draw.lines(hw.screen, wc(self.Outline), True, self.dnarrowverts[i], 5)
		# need to add in the value to change by l
		hw.screen.blit(self.labelrend, self.labelloc)
		self.Keys['accept'].SetKeyImages(("Accept", str(self.Value)))
		self.PaintKeys()
		pygame.display.update()
		pass


def _TriangleCorners(c, hgt, invert):
	h = .8 * hgt
	top = c[1] - h // 2
	bot = c[1] + h // 2
	left = c[0] - h // 2
	right = c[0] + h // 2
	if invert:
		return (c[0], bot), (left, top), (right, top)
	else:
		return (c[0], top), (left, bot), (right, bot)


class ListChooserSubScreen(screen.ScreenDesc):
	def __init__(self, masterscreen, choosername, slots, screenhgt, voffset, proc):
		"""
		Create subscreen(s) that allow choosing from a list
		:param masterscreen: the real screen for which this operates
		:param slots: number of slots to create per selection screen
		:param screenhgt: height of the area to be used for the list
		:param voffset: vertical offset for start of area to be used
		:param proc: function called with resultant selection index or -1 if cancelled
		"""
		screen.ScreenDesc.__init__(self, {}, masterscreen.name + '-' + choosername + '-Chooser',
								   parentscreen=masterscreen)
		self.Result = proc
		self.masterscreen = masterscreen
		self.selection = -1
		self.itemlist = []
		self.firstitem = 0
		self.NumSlots = slots
		self.ListKeySlots = {}
		self.SlotsVPos = []
		self.SlotItem = []
		vpos = voffset
		self.BackgroundColor = self.masterscreen.BackgroundColor
		self.DullKeyColor = wc(self.masterscreen.KeyColor, .5, self.BackgroundColor)
		self.CharColor = self.masterscreen.CharColor
		self.sourceheight = screenhgt // (self.NumSlots + 1)

		for i in range(self.NumSlots):
			self.SlotsVPos.append(vpos)
			self.ListKeySlots['Src' + str(i)] = toucharea.TouchPoint('Slot' + str(i),
																	 (
																		 hw.screenwidth // 2,
																		 vpos + self.sourceheight // 2),
																	 (hw.screenwidth, self.sourceheight),
																	 proc=functools.partial(self.PickItem, i))
			vpos += self.sourceheight
			self.SlotItem.append('')
		self.SrcPrev = (hw.screenwidth - self.sourceheight - self.HorizBorder,
						voffset - self.sourceheight // 2)
		self.SrcNext = (hw.screenwidth - self.sourceheight - self.HorizBorder,
						vpos + self.sourceheight // 2 + 10)  # for appearance
		self.ListKeySlots['Prev'] = toucharea.TouchPoint('Prev', self.SrcPrev,
														 (self.sourceheight, self.sourceheight),
														 proc=functools.partial(self.PrevNext, False))
		self.ListKeySlots['Next'] = toucharea.TouchPoint('Next', self.SrcNext,
														 (self.sourceheight, self.sourceheight),
														 proc=functools.partial(self.PrevNext, True))
		self.ListKeySlots['OKSrc'] = toucharea.ManualKeyDesc(self, 'OKSrc', ['OK'], self.BackgroundColor,
															 self.CharColor, self.CharColor,
															 center=(
																 self.SrcNext[0] - 2.5 * self.sourceheight,
																 self.SrcNext[1]),
															 size=(2 * self.sourceheight, self.sourceheight), KOn='',
															 KOff='',
															 proc=functools.partial(self.PickItemOK, True))
		'''
		self.ListKeySlots['CnclSrc'] = toucharea.ManualKeyDesc(self, 'CnclSrc', ['Back'], self.BackgroundColor,
															   self.CharColor, self.CharColor,
															   center=(
																   self.SrcNext[0] - 5 * self.sourceheight,
																   self.SrcNext[1]),
															   size=(2 * self.sourceheight, self.sourceheight), KOn='',
															   KOff='',
															   proc=functools.partial(self.PickItemOK, False))
	   '''

	# noinspection PyUnusedLocal
	def PickItem(self, slotnum):
		toucheditem = self.firstitem + slotnum
		self.selection = toucheditem if self.selection != toucheditem else -1
		self.ReInitDisplay()

	# noinspection PyUnusedLocal
	def PickItemOK(self, doit):
		if doit:
			self.Result(self.selection)
		else:
			self.Result(-1)
		screens.DS.SwitchScreen(screen.BACKTOKEN, 'Bright', 'Back from Item Pick')

	# noinspection PyUnusedLocal
	def PrevNext(self, nxt):
		if nxt:
			if self.firstitem + self.NumSlots < len(self.itemlist):
				self.firstitem += self.NumSlots
		elif self.firstitem - self.NumSlots >= 0:
			self.firstitem -= self.NumSlots
		self.ReInitDisplay()

	def Initialize(self, itemlist):
		self.itemlist = itemlist
		self.Keys = self.ListKeySlots
		self.firstitem = 0
		self.selection = -1

	def InitDisplay(self, nav):
		super(ListChooserSubScreen, self).InitDisplay(nav)
		self.DisplayListSelect()

	def ReInitDisplay(self):
		super(ListChooserSubScreen, self).ReInitDisplay()
		self.DisplayListSelect()

	def DisplayListSelect(self):
		for i in range(self.firstitem, min(len(self.itemlist), self.firstitem + self.NumSlots)):
			slot = i - self.firstitem
			clr = self.DullKeyColor if i == self.selection else self.CharColor
			rs, h, w = screenutil.CreateTextBlock(self.itemlist[i], self.sourceheight, clr, False, FitLine=True,
												  MaxWidth=hw.screenwidth - self.HorizBorder * 2)
			voff = self.SlotsVPos[slot] + (self.sourceheight - h) // 2
			hw.screen.blit(rs, (self.HorizBorder, voff))
		upcolor = wc(self.CharColor) if self.firstitem != 0 else self.DullKeyColor
		dncolor = wc(self.CharColor) if self.firstitem + self.NumSlots < len(self.itemlist) else self.DullKeyColor
		pygame.draw.polygon(hw.screen, upcolor, _TriangleCorners(self.SrcPrev, self.sourceheight, False), 3)
		pygame.draw.polygon(hw.screen, dncolor, _TriangleCorners(self.SrcNext, self.sourceheight, True), 3)
		pygame.display.update()
