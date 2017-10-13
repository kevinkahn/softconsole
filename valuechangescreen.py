import pygame
import screen
import config
import webcolors as wc
import utilities
import functools
from pygame import draw
from toucharea import TouchPoint, ManualKeyDesc


def ShowVarChangeScreen(varid, varname, initvalue):
	pass


"""
proc to draw triangle with number in middle, up/down with underlying touch area
start with center of triangle; compute the 3 vertices; do a draw aalines using them; need to scale for screen w/h

arrowsize = scaleH(40)
self.Background = KeyColorOn
self.Outline = KeyOnOutlineColor
self.CharColor = KeyCharColorOn
pygame.draw.aalines(Surf,Color,True,[[y+arrowsize/2,x], [y - arrowsize/2,x+arrowsize/2], [y - arrowsize/2,x-arrowsize/2]]
"""


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

	def __init__(self, Background, Outline, CharColor, label, initvalue, changevals, setvalueproc, returnscreen):
		self.__dict__.update({k: v for k, v in locals().items() if k != 'self'})
		self.Keys = {}
		vertzonepct = .8
		vertzonesize = int(.25*config.screenheight)
		screencenter = (config.screenheight/2, config.screenwidth/2)

		valuebuttonsize = (config.screenwidth/2, int(vertzonesize*vertzonepct))
		valuebuttoncenter = screencenter

		arrowhalfsize = int(vertzonesize*vertzonepct/2)
		uparrowcenter = []
		dnarrowcenter = []
		for i in range(len(changevals)):
			uparrowcenter.append((screencenter[0] + vertzonesize, (i + 1)*config.screenwidth/(len(changevals) + 1)))
			self.Keys['up' + str(i)] = TouchPoint('up' + str(i), uparrowcenter[
				-11, 2*arrowhalfsize, functools.partial(self.ValChange, changevals[i])])
			dnarrowcenter.append((screencenter[0] - vertzonesize, (i + 1)*config.screenwidth/(len(changevals) + 1)))
			self.Keys['dn' + str(i)] = TouchPoint('up' + str(i),
												  uparrowcenter[-11, 2*arrowhalfsize, functools.partial(self.ValChange,
																										-changevals[
																											i])])
		# create pointlist for verticies

		uparrow = [[arrowhalfsize, 0], [-arrowhalfsize, arrowhalfsize],
				   [-arrowhalfsize, -arrowhalfsize]]  # verticies ref 0,0 center
		dnarrow = [[-arrowhalfsize, 0], [arrowhalfsize, arrowhalfsize], [arrowhalfsize, -arrowhalfsize]]

		titlecenter = (screencenter[0] - int(1.75*vertzonesize), screencenter[1])
		cancelcenter = (screencenter[0] + int(1.75*vertzonesize), screencenter[1])
		cancelsize = (int(vertzonepct*config.screenheight*.125), config.screenwidth/2)

		self.Keys['cancel'] = ManualKeyDesc(self, 'cancel', 'Cancel', Background, CharColor, CharColor, cancelcenter,
											cancelsize, Proc=self.CancelChange)
		self.Keys['accept'] = ManualKeyDesc(self, 'accept', label, Background, CharColor, CharColor, valuebuttoncenter,
											valuebuttonsize, self.AcceptChange)
		# need to insert current value (actually in PaintKey probably
		pass

	def InitDisplay(self, nav):
		super(ValueChangeScreen, self).InitDisplay(nav)
		# need to write title, need to put value in accept key, need to draw arrows
		config.screen.fill(wc(self.Background))
		pygame.draw.lines(Surf, self.Outline, True, pointlist, width=2)
		# need to add in the value to change by or make this an aalines call
		self.PaintKeys()
		pygame.display.update()


"""
		pygame.draw.lines(Surf, self.Outline, True, map(functools.partial(self.offsetpoint,center),uparrow), width = 2)
		# want this to really have a param that is center so can use in a loop easily

		new_list = [x + 1 for x in my_list]
		[sum(x) for x in zip(center, p in uparrow)]
		[5, 7, 9]
		
		map(functools.partial(offsetpoint, center), uparrow)
"""

print "start"
config.screenwidth = 320
config.screenheight = 480
print config.screenheight, config.screenwidth
s = ValueChangeScreen('red', 'black', 'blue', 'Test Valchange', 7, (1,), None, None)
print 'end'
