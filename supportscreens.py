import screen
import debug
import config
import utilities
from utilfuncs import wc
import functools
import pygame
from pygame import draw
from toucharea import TouchPoint, ManualKeyDesc
import logsupport
from logsupport import ConsoleDetail
import toucharea
import screenutil


class VerifyScreen(screen.BaseKeyScreenDesc):

	def __init__(self, key, gomsg, nogomsg, proc, callingscreen, bcolor, keycoloroff, charcolor, state, interestlist):
		self.TitleFontSize=0
		self.SubFontSize=0

		debug.debugPrint('Screen', "Build Verify Screen")
		screen.BaseKeyScreenDesc.__init__(self, {}, key.name+' Verify')
		self.HubInterestList = interestlist
		self.DimTO = 20
		self.PersistTO = 10
		self.label = screen.FlatenScreenLabel(key.label)
		self.CallingScreen = callingscreen
		utilities.LocalizeParams(self, None, '-', TitleFontSize=40, SubFontSize=25)
		self.Keys['yes'] = ManualKeyDesc(self, 'yes', gomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['yes'].Proc = functools.partial(proc, True)
		self.Keys['no'] = ManualKeyDesc(self, 'no', nogomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['no'].Proc = functools.partial(proc, False)

		topoff = self.TitleFontSize + self.SubFontSize
		self.LayoutKeys(topoff, config.screenheight - 2*config.topborder - topoff)
		utilities.register_example("VerifyScreen", self)

	def Invoke(self):
		config.DS.SwitchScreen(self, 'Bright', config.DS.state, 'Do Verify ' + self.name, NavKeys=False)

	def ShowScreen(self):
		self.PaintBase()
		r = config.fonts.Font(self.TitleFontSize, '', True, True).render(self.label, 0, wc(self.CharColor))
		rl = (config.screenwidth - r.get_width())/2
		config.screen.blit(r, (rl, config.topborder))
		self.PaintKeys()
		pygame.display.update()

	def InitDisplay(self, nav):
		# debugPrint('Main', "Enter to screen: ", self.name)
		logsupport.Logs.Log('Entering Verify Screen: ' + self.name, severity=ConsoleDetail)
		super(VerifyScreen, self).InitDisplay({})
		self.ShowScreen()


class ValueChangeScreen(screen.ScreenDesc): # todo may need to call super class
	# need to set no nav keys
	@staticmethod
	def offsetpoint(center, point):
		return center[0] + point[0], center[1] + point[1]

	def CancelChange(self, presstype):
		pass

	def AcceptChange(self, presstype):
		pass

	def ValChange(self, delta, presstype):
		pass

	# noinspection PyMissingConstructor
	def __init__(self, BackgroundColor, Outline, CharColor, label, initvalue, changevals, setvalueproc, returnscreen):
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
		vertzonesize = int(.25*config.screenheight)
		screencenter = (config.screenwidth/2, config.screenheight/2)

		self.font = config.fonts.Font(40)

		self.arrowht = int(vertzonesize*vertzonepct)
		self.arrowwd = min(.8*(config.screenwidth/len(changevals)), self.arrowht)
		self.uparrowcenter = []
		self.dnarrowcenter = []
		self.uparrowverts = []
		self.dnarrowverts = []
		self.uparrow = [[0, self.arrowht/2], [self.arrowwd/2, -self.arrowht/2],
						[-self.arrowwd/2, -self.arrowht/2]]  # verticies ref 0,0 center
		self.dnarrow = [[0, -self.arrowht/2], [self.arrowwd/2, self.arrowht/2], [-self.arrowwd/2, self.arrowht/2]]
		self.chgval = []

		for i in range(len(changevals)):
			self.uparrowcenter.append(
				((i + .5)*config.screenwidth/(len(changevals)), screencenter[1] + vertzonesize))
			self.Keys['up' + str(i)] = TouchPoint('up' + str(i), self.uparrowcenter[
				-1], self.arrowwd, functools.partial(self.ValChange, changevals[i]))
			self.uparrowverts.append(
				[functools.partial(self.offsetpoint, self.uparrowcenter[-1])(self.uparrow[k]) for k in range(3)])
			self.dnarrowcenter.append(
				((i + .5)*config.screenwidth/(len(changevals)), screencenter[1] - vertzonesize))
			self.Keys['dn' + str(i)] = TouchPoint('up' + str(i), self.dnarrowcenter[
				-1], self.arrowwd, functools.partial(self.ValChange, -changevals[i]))
			self.dnarrowverts.append(
				[functools.partial(self.offsetpoint, self.dnarrowcenter[-1])(self.dnarrow[k]) for k in range(3)])
			fs = self.font.size(str(changevals[i]))
			self.chgval.append(
				((-fs[0]/2, fs[1]), self.font.render(str(changevals[i]), True, wc(CharColor))))

		self.titlecenter = (screencenter[0] - int(1.75*vertzonesize), screencenter[1])
		valuebuttoncenter = screencenter
		valuebuttonsize = (config.screenwidth/2, int(vertzonesize*vertzonepct))
		labelcenter = (screencenter[0], screencenter[1] - int(1.75*vertzonesize))
		self.labelrend = self.font.render(label, True, wc(CharColor))
		labelsz = self.font.size(label)
		self.labelloc = (labelcenter[0] - labelsz[0]/2, labelcenter[1] - labelsz[1]/2)

		cancelcenter = (screencenter[0], screencenter[1] + int(1.75*vertzonesize))
		cancelsize = (config.screenwidth/2, int(vertzonepct*config.screenheight*.125))

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

		self.PaintBase()
		# write the title with name of var? maybe button should be "accept"
		for i in range(len(self.changevals)):
			fho = self.chgval[i][0][0]
			fvo = self.chgval[i][0][1]
			config.screen.blit(self.chgval[i][1],
							   self.offsetpoint(self.uparrowcenter[i], (fho, -self.arrowht/2 + self.arrowht/10)))
			config.screen.blit(self.chgval[i][1],
							   self.offsetpoint(self.dnarrowcenter[i], (fho, self.arrowht/2 - fvo - self.arrowht/10)))
			draw.lines(config.screen, wc(self.Outline), True, self.uparrowverts[i], 5)
			draw.lines(config.screen, wc(self.Outline), True, self.dnarrowverts[i], 5)
		# need to add in the value to change by l
		config.screen.blit(self.labelrend, self.labelloc)
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
	def __init__(self, masterscreen, slots, screenhgt, voffset, proc):
		"""
		Create subscreen(s) that allow choosing from a list
		:param masterscreen: the real screen for which this operates
		:param slots: number of slots to create per selection screen
		:param screenhgt: height of the area to be used for the list
		:param voffset: vertical offset for start of area to be used
		:param proc: function called with resultant selection index or -1 if cancelled
		"""
		self.Result = proc
		self.masterscreen = masterscreen
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
																		 config.screenwidth // 2,
																		 vpos + self.sourceheight // 2),
																	 (config.screenwidth, self.sourceheight),
																	 proc=functools.partial(self.PickItem, i))
			vpos += self.sourceheight
			self.SlotItem.append('')
		self.SrcPrev = (config.screenwidth - self.sourceheight - config.horizborder,
						voffset - self.sourceheight // 2)
		self.SrcNext = (config.screenwidth - self.sourceheight - config.horizborder,
						vpos + self.sourceheight // 2 + 10)  # for appearance
		self.ListKeySlots['Prev'] = toucharea.TouchPoint('Prev' + str(i), self.SrcPrev,
														 (self.sourceheight, self.sourceheight),
														 proc=functools.partial(self.PrevNext, False))
		self.ListKeySlots['Next'] = toucharea.TouchPoint('Next' + str(i), self.SrcNext,
														 (self.sourceheight, self.sourceheight),
														 proc=functools.partial(self.PrevNext, True))
		self.ListKeySlots['OKSrc'] = toucharea.ManualKeyDesc(screen, 'OKSrc', ['OK'], self.BackgroundColor,
															 self.CharColor, self.CharColor,
															 center=(
																 self.SrcNext[0] - 2.5 * self.sourceheight,
																 self.SrcNext[1]),
															 size=(2 * self.sourceheight, self.sourceheight), KOn='',
															 KOff='',
															 proc=functools.partial(self.PickItemOK, True))
		self.ListKeySlots['CnclSrc'] = toucharea.ManualKeyDesc(screen, 'CnclSrc', ['Back'], self.BackgroundColor,
															   self.CharColor, self.CharColor,
															   center=(
																   self.SrcNext[0] - 5 * self.sourceheight,
																   self.SrcNext[1]),
															   size=(2 * self.sourceheight, self.sourceheight), KOn='',
															   KOff='',
															   proc=functools.partial(self.PickItemOK, False))

	def PickItem(self, slotnum, presstype):
		# print(slotnum)
		# change the source
		self.selection = self.firstitem + slotnum
		self.masterscreen.ShowScreen()

	def PickItemOK(self, doit, presstype):
		if doit:
			self.Result(self.selection)
		else:
			self.Result(-1)

	def PrevNext(self, nxt, presstype):
		if nxt:
			if self.firstitem + self.NumSlots < len(self.itemlist):
				self.firstitem += self.NumSlots
		elif self.firstitem - self.NumSlots >= 0:
			self.firstitem -= self.NumSlots
		self.masterscreen.ShowScreen()

	def Initialize(self, itemlist):
		self.itemlist = itemlist
		self.masterscreen.Keys = self.ListKeySlots
		self.firstitem = 0
		self.selection = -1

	def DisplayListSelect(self):
		self.masterscreen.ReInitDisplay()
		for i in range(self.firstitem, min(len(self.itemlist), self.firstitem + self.NumSlots)):
			slot = i - self.firstitem
			clr = self.DullKeyColor if i == self.selection else self.CharColor
			rs, h, w = screenutil.CreateTextBlock(self.itemlist[i], self.sourceheight, clr, False, FitLine=True,
												  MaxWidth=config.screenwidth - config.horizborder * 2)
			# self.SourceSlot[slot] = self.SourceSet[i]
			voff = self.SlotsVPos[slot] + (self.sourceheight - h) // 2
			config.screen.blit(rs, (config.horizborder, voff))
		pygame.draw.polygon(config.screen, wc(self.CharColor),
							_TriangleCorners(self.SrcPrev, self.sourceheight, False), 3)
		pygame.draw.polygon(config.screen, wc(self.CharColor),
							_TriangleCorners(self.SrcNext, self.sourceheight, True), 3)
		pygame.display.update()
