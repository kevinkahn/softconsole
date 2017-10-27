import screen
import config
import utilities
from utilities import wc
import functools
import pygame
import fonts, debug
from pygame import draw
from toucharea import TouchPoint, ManualKeyDesc

class ValueChangeScreen(screen.ScreenDesc):
	# need to set no nav keys
	@staticmethod
	def offsetpoint(center, point):
		return (center[0] + point[0], center[1] + point[1])

	def CancelChange(self, presstype):
		pass

	def AcceptChange(self, presstype):
		pass

	def ValChange(self, delta):
		pass

	def __init__(self, BackgroundColor, Outline, CharColor, label, initvalue, changevals, setvalueproc, returnscreen):
		self.__dict__.update({k: v for k, v in locals().items() if k != 'self'})
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

		config.screen.fill(wc(self.BackgroundColor))
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


utilities.InitializeEnvironment()
debug.Flags = debug.InitFlags()

print "start"
# config.screenwidth = 320
#config.screenheight = 480
print config.screenheight, config.screenwidth
s = ValueChangeScreen('red', 'black', 'blue', 'Test Valchange', 7, (1, 10, 100), None, None)
s.InitDisplay(1)
print 'end'
