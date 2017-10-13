import screen
import config
import webcolors as wc
from utilities import wc
import functools
import pygame
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

	def __init__(self, Background, Outline, CharColor, label, initvalue, changevals, setvalueproc, returnscreen):
		self.__dict__.update({k: v for k, v in locals().items() if k != 'self'})
		self.Value = initvalue
		self.Keys = {}
		vertzonepct = .8
		vertzonesize = int(.25*config.screenheight)
		screencenter = (config.screenheight/2, config.screenwidth/2)

		arrowhalfsize = int(vertzonesize*vertzonepct/2)
		self.uparrowcenter = []
		self.dnarrowcenter = []
		self.uparrow = [[arrowhalfsize, 0], [-arrowhalfsize, arrowhalfsize],
						[-arrowhalfsize, -arrowhalfsize]]  # verticies ref 0,0 center
		self.dnarrow = [[-arrowhalfsize, 0], [arrowhalfsize, arrowhalfsize], [arrowhalfsize, -arrowhalfsize]]

		for i in range(len(changevals)):
			self.uparrowcenter.append(
				(screencenter[0] + vertzonesize, (i + 1)*config.screenwidth/(len(changevals) + 1)))
			self.Keys['up' + str(i)] = TouchPoint('up' + str(i), self.uparrowcenter[
				-11, 2*arrowhalfsize, functools.partial(self.ValChange, changevals[i])])
			self.uparrowverts = \
				[map(functools.partial(self.offsetpoint, self.uparrowcenter[-1]), self.uparrow[k]) for k in range(3)]
			self.dnarrowcenter.append(
				(screencenter[0] - vertzonesize, (i + 1)*config.screenwidth/(len(changevals) + 1)))
			self.Keys['dn' + str(i)] = TouchPoint('up' + str(i),
												  self.dnarrowcenter[
													  -11, 2*arrowhalfsize, functools.partial(self.ValChange,
																							  -changevals[i])])
			self.dnarrowverts = \
				[map(functools.partial(self.offsetpoint, self.dnarrowcenter[-1]), self.dnarrow[k]) for k in range(3)]

		self.titlecenter = (screencenter[0] - int(1.75*vertzonesize), screencenter[1])
		valuebuttoncenter = screencenter
		valuebuttonsize = (config.screenwidth/2, int(vertzonesize*vertzonepct))
		cancelcenter = (screencenter[0] + int(1.75*vertzonesize), screencenter[1])
		cancelsize = (int(vertzonepct*config.screenheight*.125), config.screenwidth/2)

		self.Keys['cancel'] = ManualKeyDesc(self, 'cancel', 'Cancel', Background, CharColor, CharColor, cancelcenter,
											cancelsize, Proc=self.CancelChange)
		self.Keys['accept'] = ManualKeyDesc(self, 'accept', ["Accept", "#"], Background, CharColor, CharColor,
											valuebuttoncenter,
											valuebuttonsize, self.AcceptChange)
		# need to insert current value (actually in PaintKey probably
		pass

	def InitDisplay(self, nav):
		super(ValueChangeScreen, self).InitDisplay(nav)

		config.screen.fill(wc(self.Background))
		# write the title with name of var? maybe button should be "accept"
		for i in range(len(self.changevals)):
			draw.lines(config.screen, self.Outline, True, self.uparrowverts, width=2)
			draw.lines(config.screen, self.Outline, True, self.dnarrowverts, width=2)
		# need to add in the value to change by or make this an aalines call
		self.Keys['accept'].SetKeyImages(("Accept", str(self.Value)))
		self.PaintKeys()
		pygame.display.update()



print "start"
config.screenwidth = 320
config.screenheight = 480
print config.screenheight, config.screenwidth
s = ValueChangeScreen('red', 'black', 'blue', 'Test Valchange', 7, (1,), None, None)
print 'end'
