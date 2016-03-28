import config
import utilities
import pygame
import webcolors
from utilities import scaleW, scaleH
wc = webcolors.name_to_rgb


def InBut(pos, Key):
	return (pos[0] > Key.Center[0] - Key.Size[0]/2) and (pos[0] < Key.Center[0] + Key.Size[0]/2) and \
		   (pos[1] > Key.Center[1] - Key.Size[1]/2) and (pos[1] < Key.Center[1] + Key.Size[1]/2)


class TouchPoint(object):
	"""
	Represents a touchable rectangle on the screen.
	"""

	def __init__(self, c, s):
		self.Center = c
		self.Size = s
		utilities.register_example("TouchPoint", self)


class ManualKeyDesc(TouchPoint):
	"""
	Defines a drawn touchable rectangle on the screen that represents a key (button).  May be called with one of 2
	signatures.  It can be called manually by code to create a key by supplying all the attributes of the key in the
	code explicitly.  It can also be called with a config objects section in which case it will build the key from the
	combination of the defaults for the attributes and the explicit overides found in the config.txt file section
	that is passed in.
	"""

	def __init__(self, *args, **kwargs):
		# alternate creation signatures
		self.ButtonFontSizes = tuple(scaleH(i) for i in (31, 28, 25, 22, 20, 18, 16))  # todo pixel - also is this the right place for this
		self.DynamicLabel = False
		if len(args) == 2:
			# signature: ManualKeyDesc(keysection, keyname)
			# initialize by reading config file
			self.dosectioninit(*args)
		else:
			# signature: ManualKeyDesc(keyname, label, bcolor, charcoloron, charcoloroff, center=, size=, KOn=, KOff=, proc=)
			# initializing from program code case
			self.docodeinit(*args, **kwargs)
		utilities.register_example("ManualKeyDesc", self)

	def docodeinit(self, keyname, label, bcolor, charcoloron, charcoloroff, DynamicLabel = False, center=(0, 0), size=(0, 0), KOn='', KOff='',
				   proc=None):
		# NOTE: do not put defaults for KOn/KOff in signature - imports and arg parsing subtleties will cause error
		# because of when config is imported and what walues are at that time versus at call time
		TouchPoint.__init__(self, center, size)
		self.name = keyname
		self.RealObj = proc
		self.KeyColor = bcolor
		self.KeyCharColorOn = charcoloron
		self.KeyCharColorOff = charcoloroff
		self.State = True
		self.label = label
		if label[0] == '':
			self.DynamicLabel = True
		self.KeyOnOutlineColor = config.KeyOnOutlineColor if KOn == '' else KOn
		self.KeyOffOutlineColor = config.KeyOffOutlineColor if KOff == '' else KOff

	def dosectioninit(self, keysection, keyname):
		TouchPoint.__init__(self, (0, 0), (0, 0))
		utilities.LocalizeParams(self, keysection, 'KeyColor', 'KeyOffOutlineColor', 'KeyOnOutlineColor',
								 'KeyCharColorOn', 'KeyCharColorOff', label=[keyname])
		self.name = keyname
		self.State = True
		self.RealObj = None  # this will get filled in by creator later - could be ISY node, ISY program, proc to call

	def PaintKey(self,latetitle=None):
		x = self.Center[0] - self.Size[0]/2
		y = self.Center[1] - self.Size[1]/2
		if self.State:
			if self.DynamicLabel:
				temp = self.KeyOnImage.copy()
				self.AddTitle(temp,latetitle,self.FindFontSize(latetitle,0,True),self.KeyCharColorOn)
				config.screen.blit(temp,(x,y))
			else:
				config.screen.blit(self.KeyOnImage,(x,y))
		else:
			if self.DynamicLabel:
				temp = self.KeyOffImage.copy()
				self.AddTitle(temp,latetitle,self.FindFontSize(latetitle,0,True),self.KeyCharColorOff)
				config.screen.blit(temp,(x,y))
			else:
				config.screen.blit(self.KeyOffImage,(x,y))
		pygame.display.update()

	def FindFontSize(self,lab,firstfont,shrink):
		lines = len(lab)
		buttonsmaller = (self.Size[0] - scaleW(6), self.Size[1] - scaleH(6))  # todo pixel
		# compute writeable area for text
		textarea = (buttonsmaller[0] - 2, buttonsmaller[1] - 2)  # todo pixel not scaled
		fontchoice = self.ButtonFontSizes[firstfont]
		if shrink:
			for l in range(lines):
				for i in range(firstfont, len(self.ButtonFontSizes) - 1):
					txtsize = config.fonts.Font(self.ButtonFontSizes[i]).size(lab[l])
					if lines*txtsize[1] >= textarea[1] or txtsize[0] >= textarea[0]:
						fontchoice = self.ButtonFontSizes[i + 1]
		return fontchoice

	def AddTitle(self,surface,label,fontchoice,color):
		lines = len(label)
		for i in range(lines):
			ren = config.fonts.Font(fontchoice).render(label[i], 0, wc(color))
			vert_off = ((i + 1)*self.Size[1]/(1 + lines)) - ren.get_height()/2
			horiz_off = (self.Size[0] - ren.get_width())/2
			surface.blit(ren, (horiz_off,vert_off))

	def FinishKey(self,center,size,firstfont=0,shrink=True):
		if size[0] <> 0: # if size is not zero then set the pos/size of the key; otherwise it was previously set in manual creation
			self.Center = center
			self.Size = size

		buttonsmaller = (self.Size[0] - scaleW(6), self.Size[1] - scaleH(6))  # todo pixel

		# create image of ON key
		self.KeyOnImage = pygame.Surface(self.Size)
		pygame.draw.rect(self.KeyOnImage, wc(self.KeyColor), ((0, 0), self.Size), 0)
		bord = 3  # todo pixel - probably should use same scaling in both dimensions since this is a line width
		pygame.draw.rect(self.KeyOnImage, wc(self.KeyOnOutlineColor), ((scaleW(bord),scaleH(bord)), buttonsmaller), bord)

		# create image of OFF key
		self.KeyOffImage = pygame.Surface(self.Size)
		pygame.draw.rect(self.KeyOffImage, wc(self.KeyColor), ((0, 0), self.Size), 0)
		bord = 3  # todo pixel - probably should use same scaling in both dimensions since this is a line width
		pygame.draw.rect(self.KeyOffImage, wc(self.KeyOffOutlineColor), ((scaleW(bord),scaleH(bord)), buttonsmaller), bord)
		s = pygame.Surface(self.Size)
		s.set_alpha(150)
		s.fill(wc("white"))
		self.KeyOffImage.blit(s, (0,0))

		# if a non-blank label then add in the label - otherwise it is a late bound label that will get set at paint time
		if not self.DynamicLabel:
			fontchoice = self.FindFontSize(self.label,firstfont,shrink)
			self.AddTitle(self.KeyOnImage,self.label,fontchoice,self.KeyCharColorOn)
			self.AddTitle(self.KeyOffImage,self.label,fontchoice,self.KeyCharColorOff)


