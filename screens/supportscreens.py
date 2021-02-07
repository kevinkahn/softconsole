import functools

import pygame
from pygame import draw
import inspect

import debug
import logsupport
from screens import screen, screenutil
import screens.__screens as screens
from utils import utilities, fonts, displayupdate, hw
from logsupport import ConsoleDetail
from keyspecs import toucharea
from utils.utilfuncs import wc
from guicore.switcher import SwitchScreen

class VerifyScreen(screen.BaseKeyScreenDesc):

	def __init__(self, key, gomsg, nogomsg, procyes, callingscreen, bcolor, keycoloroff, charcolor, state,
				 interestlist, SingleUse=False):
		super().__init__({}, key.Screen.name + '-' + key.name + '-Verify', parentscreen=key, SingleUse=SingleUse)
		debug.debugPrint('Screen', "Build Verify Screen")
		self.callingkey = key
		self.yesproc = procyes
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.HubInterestList = interestlist
		self.DimTO = 20
		self.PersistTO = 10
		self.label = screen.FlatenScreenLabel(key.label)
		self.ClearScreenTitle()  # don't use parent screen title
		self.CallingScreen = callingscreen  # todo either eliminare or use for something - note could be none from maint exit
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.SetScreenTitle(self.label, 40, charcolor)
		self.Keys['yes'] = toucharea.ManualKeyDesc(self, 'yes', gomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['yes'].Proc = self.Verified
		self.Keys['no'] = toucharea.ManualKeyDesc(self, 'no', nogomsg, bcolor, keycoloroff, charcolor, State=state)
		self.Keys['no'].Proc = functools.partial(screen.PopScreen, 'Verify denied')

		self.LayoutKeys(self.startvertspace, self.useablevertspacesansnav)
		key.Screen.ChildScreens[key.name + '-Verify'] = self
		utilities.register_example("VerifyScreen", self)

	def Verified(self):
		if 'Key' in inspect.signature(self.yesproc).parameters:
			self.yesproc(Key=self.callingkey)
		else:
			self.yesproc()
		screen.PopScreen('Verified')

	def Invoke(self):
		screen.PushToScreen(self, msg='Do Verify' + self.name)

	def InitDisplay(self, nav):
		# debugPrint('Main', "Enter to screen: ", self.name)
		logsupport.Logs.Log('Entering Verify Screen: ' + self.name, severity=ConsoleDetail)
		super(VerifyScreen, self).InitDisplay({})

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
		super().__init__({}, label + ' -ValChange')
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
			self.Keys['up' + str(i)] = toucharea.TouchPoint('up' + str(i), self.uparrowcenter[
				-1], self.arrowwd, functools.partial(self.ValChange, changevals[i]))
			self.uparrowverts.append(
				[functools.partial(self.offsetpoint, self.uparrowcenter[-1])(self.uparrow[k]) for k in range(3)])
			self.dnarrowcenter.append(
				((i + .5) * hw.screenwidth / (len(changevals)), screencenter[1] - vertzonesize))
			self.Keys['dn' + str(i)] = toucharea.TouchPoint('up' + str(i), self.dnarrowcenter[
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

		self.Keys['cancel'] = toucharea.ManualKeyDesc(self, 'cancel', ['Cancel', ], BackgroundColor, CharColor,
													  CharColor,
													  cancelcenter,
													  cancelsize, proc=self.CancelChange)
		self.Keys['accept'] = toucharea.ManualKeyDesc(self, 'accept', ["Accept", "#"], BackgroundColor, CharColor,
													  CharColor,
													  valuebuttoncenter,
													  valuebuttonsize, proc=self.AcceptChange)
		# need to insert current value (actually in PaintKey probably
		pass

	def InitDisplay(self, nav):  # todo integrate with specific repaint stuff
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
		displayupdate.updatedisplay()
		pass


def TriangleCorners(c, hgt, invert):
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
		super().__init__({}, masterscreen.name + '-' + choosername + '-Chooser',
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
		SwitchScreen(screen.BACKTOKEN, 'Bright', 'Back from Item Pick')

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

	def InitDisplay(self, nav):  # todo move the DisplayListSelect to specific repaint
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
		pygame.draw.polygon(hw.screen, upcolor, TriangleCorners(self.SrcPrev, self.sourceheight, False), 3)
		pygame.draw.polygon(hw.screen, dncolor, TriangleCorners(self.SrcNext, self.sourceheight, True), 3)
		displayupdate.updatedisplay()  # todo delete once specific screen is used


class PagedDisplay(screen.BaseKeyScreenDesc):
	def __init__(self, nm, StartPosChooser, LineRenderer, GetPageHeader, fontsize,
				 color):  # todo = blanks until reinit repaints
		super().__init__(None, nm)
		self.SetScreenClock(.25)
		self.BackgroundColor = 'maroon'
		self.StartChooser = StartPosChooser
		self.LineRenderer = LineRenderer
		self.GetPageHeader = GetPageHeader
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.state = 'init'  # init: new entry to logs; scroll: doing error scroll manual: user control
		self.startat = 0  # where in log page starts
		self.startpage = 0
		self.item = 0
		self.pageno = -1
		self.oknext = True
		self.PageStartItem = [0]
		self.Keys = {'nextpage': toucharea.TouchPoint('nextpage', (hw.screenwidth / 2, 3 * hw.screenheight / 4),
													  (hw.screenwidth, hw.screenheight / 2), proc=self.NextPage,
													  procdbl=self.BotPage),
					 'prevpage': toucharea.TouchPoint('prevpage', (hw.screenwidth / 2, hw.screenheight / 4),
													  (hw.screenwidth, hw.screenheight / 2),
													  proc=self.PrevPage, procdbl=self.TopPage)}
		self.color = color
		self.pagefont = fonts.fonts.Font(fontsize, face=fonts.monofont)
		utilities.register_example("LogDisplayScreen", self)

	# noinspection PyUnusedLocal
	def NextPage(self):
		if not self.oknext: return  # need to render previous call first
		if self.item >= 0:
			self.pageno += 1
			self.startpage = self.item
			self.oknext = False
		else:
			if self.state != 'scroll':
				self.state = 'init'
				SwitchScreen(screen.BACKTOKEN, 'Bright', 'Done (next) showing log', newstate='Maint')
			else:
				self.state = 'manual'

	# noinspection PyUnusedLocal
	def PrevPage(self):
		if not self.oknext: return
		if self.pageno > 0:
			self.pageno -= 1
			self.oknext = False
			self.startpage = self.PageStartItem[self.pageno]
		else:
			self.state = 'init'
			SwitchScreen(screen.BACKTOKEN, 'Bright', 'Done (prev) showing log', newstate='Maint')

	def TopPage(self):
		self.pageno = 0
		self.item = 0
		self.startpage = self.PageStartItem[0]
		self.oknext = False

	def BotPage(self):
		self.state = 'scroll'
		self.startat = 99999999999

	def ScreenContentRepaint(self):
		self.item = self.RenderPage(self.BackgroundColor, start=self.startpage, pageno=self.pageno)
		if self.pageno + 1 == len(self.PageStartItem):  # if first time we saw this page remember its start pos
			self.PageStartItem.append(self.item)
		self.oknext = True
		if self.state == 'scroll':
			if (self.item < self.startat) and (
					self.item != -1):  # if first error not yet up and not last page go to next page
				self.NextPage()
			else:
				self.state = 'manual'
		else:
			pass

	def ReInitDisplay(self):
		super().ReInitDisplay()

	def InitDisplay(self, nav):
		self.startat = self.StartChooser()
		self.startpage = 0
		self.item = 0
		self.pageno = 0
		self.PageStartItem = [0]
		self.state = 'scroll' if self.startat != 0 else 'manual'
		super().InitDisplay(nav)

	def RenderPage(self, backcolor, start=0, pageno=-1):
		moretorender = True
		itemnumber = start
		pos = 0
		hw.screen.fill(wc(backcolor))
		if pageno != -1:
			hdr, moretorender = self.GetPageHeader(pageno + 1, itemnumber)
			l = self.pagefont.render(hdr, False, wc(self.color))
			hw.screen.blit(l, (10, pos))
			pos = pos + self.pagefont.get_linesize()
		while moretorender:
			l, moretorender = self.LineRenderer(itemnumber, self.pagefont)
			hw.screen.blit(l, (10, pos))  # todo this can cause long lines to render off the screen
			pos = pos + l.get_height()
			itemnumber += 1
			if pos > hw.screenheight - screens.screenStore.BotBorder:
				return itemnumber if moretorender else -1

		l = self.pagefont.render('***** End *****', False, wc(self.color))
		hw.screen.blit(l, ((hw.screenwidth - l.get_width()) / 2, pos + l.get_height()))
		return -1


class SliderScreen(screen.BaseKeyScreenDesc):
	def __init__(self, key, charcolor, bcolor, valuegetter, valuesetter, showpct=True, rangelow=0, rangehi=100,
				 orientation=0):
		# call result setter as often as desired to show partial changes
		# assumes range of slider is 0-100%; todo override with rangelow/high to change the displayed value if desired
		# orientation: 0 use long dimension, 1: force horizontal, 2: force vertical

		super().__init__({}, key.Screen.name + '-' + key.name + '-Value', parentscreen=key)
		debug.debugPrint('Screen', "Build Verify Screen")
		self.SetScreenClock(.05)
		self.ValueGetter = valuegetter
		self.ValueSetter = valuesetter
		self.RangeLow = rangelow
		self.RangeHigh = rangehi
		self.ShowPct = showpct
		self.HorizBar = (not displayupdate.portrait, True, False)[orientation]
		# self.HorizBar = False
		self.initval = 0
		self.curval = 0
		self.WatchMotion = True
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.HubInterestList = {}
		self.DimTO = 20
		self.PersistTO = 10
		self.label = screen.FlatenScreenLabel(key.label)
		self.ClearScreenTitle()  # don't use parent screen title
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.SetScreenTitle(self.label, 40, charcolor)
		self.Keys['yes'] = toucharea.ManualKeyDesc(self, 'OK', ('OK',), bcolor, charcolor, charcolor, State=True)
		self.Keys['yes'].Proc = self.SetFinal
		self.Keys['no'] = toucharea.ManualKeyDesc(self, 'Cancel', ('Cancel',), bcolor, charcolor, charcolor, State=True)
		self.Keys['no'].Proc = self.Revert
		self.font = fonts.fonts.Font(60)

		keyheight = self.useablevertspacesansnav * .3
		self.sliderareavert = self.useablevertspacesansnav - keyheight

		self.slidelinelen = ((self.useablevertspacesansnav - keyheight) * .8, self.useablehorizspace * .8)[
			self.HorizBar]
		self.slidelinewidth = (self.useablehorizspace * .02, self.useablevertspacesansnav * .02)[self.HorizBar]

		self.slideline = self.sliderareavert

		self.slidelinestarta = (self.startvertspace + (self.sliderareavert - self.slidelinelen) / 2,
								(self.useablehorizspace - self.slidelinelen) / 2)[self.HorizBar]
		self.slidelinestartb = (self.useablehorizspace / 2, self.sliderareavert)[self.HorizBar]

		if self.HorizBar:
			self.sliderect = pygame.Rect(self.slidelinestarta, self.slidelinestartb - self.slidelinewidth / 2,
										 self.slidelinelen, self.slidelinewidth)
		else:
			self.sliderect = pygame.Rect(self.slidelinestartb - self.slidelinewidth / 2, self.slidelinestarta,
										 self.slidelinewidth, self.slidelinelen)
		self.slidebuttonrad = self.useablevertspacesansnav * .05
		self.slidecolor = charcolor
		self.LayoutKeys(self.sliderareavert, keyheight)
		key.Screen.ChildScreens[key.name + '-Slider'] = self
		utilities.register_example("SliderScreen", self)

	def Invoke(self):
		self.initval = self.ValueGetter()
		self.curval = self.initval
		print('Invoke {}'.format(self.curval))
		screen.PushToScreen(self, msg='Do Slider' + self.name)

	def InitDisplay(self, nav):
		# debugPrint('Main', "Enter to screen: ", self.name)
		print('Init stuff')
		logsupport.Logs.Log('Entering Slider Screen: ' + self.name, severity=ConsoleDetail)
		super().InitDisplay({})

	# add a reinit?
	# real work in ScreenContentRepaint

	def ScreenContentRepaint(self):
		pygame.draw.rect(hw.screen, wc(self.slidecolor), self.sliderect)
		# print('Vals {} {} {}'.format(self.curval,self.slidelinelen,self.slidelinestart))
		relpos = self.curval * self.slidelinelen / 100 + self.slidelinestarta
		fixpos = self.slidelinestartb
		center = ((int(fixpos), int(relpos)), (int(relpos), int(fixpos)))[self.HorizBar]
		pygame.draw.circle(hw.screen, wc(self.slidecolor), center, int(self.slidebuttonrad), 0)
		if self.ShowPct:
			t = self.font.render(str(int(self.curval)), False, wc(self.slidecolor))
			hw.screen.blit(t, (self.starthorizspace * 2, self.startvertspace * 2))

	def Motion(self, pos):
		# pos is x,y don't care about y just x; convert x to a position on the slider with it at end if off slider
		if pos[int(not self.HorizBar)] < self.slidelinestarta:
			nowpos = 0
		elif pos[int(not self.HorizBar)] > self.slidelinestarta + self.slidelinelen:
			nowpos = 100
		else:
			nowpos = ((pos[int(not self.HorizBar)] - self.slidelinestarta) / self.slidelinelen) * 100
		self.curval = nowpos
		# print('Val {} {} {} {} {} {}'.format(pos, nowpos, self.curval, self.slidelinestarta, self.slidelinestartb, self.slidelinelen))
		self.ValueSetter(self.curval)

	def SetFinal(self):
		self.ValueSetter(self.curval)
		screen.PopScreen('Set slider val')  # todo state param missing?

	def Revert(self):
		self.ValueSetter(self.initval)
		screen.PopScreen('Cancel slider val')
