import pygame
import pygame.gfxdraw

pg = pygame
pg.gfxdraw = pygame.gfxdraw
'''
import pygame
from pygame import gfxdraw
import inspect
import functools




class pgactual(object):
	FULLSCREEN = pygame.FULLSCREEN
	Rect = pygame.Rect

	class display(object):

		@staticmethod
		def init():
			return pygame.display.init()

		@staticmethod
		def quit():
			return pygame.display.quit()

		@staticmethod
		def set_mode(*args, **kwargs):
			return pgactual.Surface(wrap=pygame.display.set_mode(*args, **kwargs))

		@staticmethod
		def update(*args, **kwargs):
			return pygame.display.update(*args, **kwargs)

		@staticmethod
		def Info():
			return pygame.display.Info()

	class Surface(object):
		actualobj = None

		def __init__(self, *args, **kwargs):
			print('Surface: {} {} -- {}'.format(self, args, kwargs))
			if 'wrap' in kwargs:
				# print('Wrap {} -> {}'.format(kwargs['wrap'],self))
				self.actualobj = kwargs['wrap']
			else:
				self.actualobj = pygame.Surface(*args, **kwargs)
			self.dohook(*args, **kwargs)

		def dohook(self, *args, **kwargs):
			print('DoHook {} {} {}'.format(self,args,kwargs))

		def blit(self, *args, **kwargs):
			# print('Blit {}'.format(args))
			tmpargs = list(args)
			tmpargs[0] = self._unwrap(tmpargs[0])
			return self.actualobj.blit(*tmpargs, **kwargs)

		def convert_alpha(self, *args):
			tmpargs = list(args)
			if len(args) > 0:
				tmpargs[0] = self._unwrap(tmpargs[0])
				return self.actualobj.convert_alpha(*tmpargs)
			else:
				return pgactual.Surface(wrap=self.actualobj.convert_alpha())

		def set_colorkey(self, *args, **kwargs):
			return self.actualobj.set_colorkey(*args, **kwargs)

		def get_colorkey(self):
			return self.actualobj.get_colorkey()

		def fill(self, *args, **kwargs):
			print('fill {}'.format(self))
			print(self.__dict__)
			return self.actualobj.fill(*args, **kwargs)

		def get_height(self):
			return self.actualobj.get_height()

		def get_width(self):
			return self.actualobj.get_width()

		def set_alpha(self, *args, **kwargs):
			return self.actualobj.set_alpha(*args, **kwargs)

		def _unwrap(self, target):
			# print('Unwrap {} -> {}'.format(target, target.actualobj))
			return target.actualobj

		def get_locked(self):
			return self.actualobj.get_locked()

	class mouse(object):
		@staticmethod
		def set_visible(*args, **kwargs):
			return pygame.mouse.set_visible(*args, **kwargs)

	class transform(object):
		@staticmethod
		def smoothscale(*args, **kwargs):
			return pgactual.Surface(wrap=pygame.transform.smoothscale(*_unwrapSurf(*args), **kwargs))

		@staticmethod
		def rotate(*args, **kwargs):
			return pgactual.Surface(wrap=pygame.transform.rotate(*_unwrapSurf(*args), **kwargs))

	class image(object):
		@staticmethod
		def load(*args, **kwargs):
			return pgactual.Surface(wrap=pygame.image.load(*args, **kwargs))

		@staticmethod
		def save(*args, **kwargs):
			pygame.image.save(*_unwrapSurf(*args), **kwargs)

	class draw(object):

		@staticmethod
		def line(*args, **kwargs):
			return pygame.draw.line(*_unwrapSurf(*args), **kwargs)

		@staticmethod
		def lines(*args, **kwargs):
			return pygame.draw.lines(*_unwrapSurf(*args), **kwargs)

		@staticmethod
		def polygon(*args, **kwargs):
			return pygame.draw.polygon(*_unwrapSurf(*args), **kwargs)

		@staticmethod
		def rect(*args, **kwargs):
			return pygame.draw.rect(*_unwrapSurf(*args), **kwargs)

		@staticmethod
		def circle(*args, **kwargs):
			return pygame.draw.circle(*_unwrapSurf(*args), **kwargs)

	class gfxdraw(object):
		@staticmethod
		def filled_trigon(*args, **kwargs):
			return gfxdraw.filled_trigon(*_unwrapSurf(*args), **kwargs)

	# class Rect(object):
	# this is tricky to wrap but may not need to be unless other functions are called in it
	#	z = None
	#	def __init__(self, *args):
	#		self.z = pygame.Rect(*args)

	class font(object):

		class Font(object):
			actualobj = None

			def __init__(self, item):
				self.actualobj = item

			def render(self, *args, **kwargs):
				return pgactual.Surface(wrap=self.actualobj.render(*args, **kwargs))

			def size(self, *args, **kwargs):
				return self.actualobj.size(*args, **kwargs)

			def get_linesize(self, *args, **kwargs):
				return self.actualobj.get_linesize(*args, **kwargs)

		@staticmethod
		def init():
			return pygame.font.init()

		@staticmethod
		def get_fonts():
			return pygame.font.get_fonts()

		@staticmethod
		def SysFont(*args, **kwargs):
			print('Sysfont {} -- {}'.format(args,kwargs))
			y = pygame.font.SysFont(*args, **kwargs)
			return pgactual.font.Font(y)

	def init(self):
		return pygame.init()

	def quit(self):
		return pygame.quit()


def _unwrapSurf(*args):
	tempargs = list(args)
	tempargs[0] = tempargs[0]._unwrap(tempargs[0])
	return tempargs

def DoRemoteCall(cls, meth, self, *args, **kwargs):
	print('Issue call for {}.{} with {},{}'.format(cls, meth, args, kwargs))
	print(pg.actualclass[cls][meth])
	res = pg.actualclass[cls][meth](self, *args,**kwargs)
	return res

def DoRemoteCallStatic(cls, meth, *args, **kwargs):
	print('Issue call for {}.{} with {},{}'.format(cls, meth, args, kwargs))
	print(pg.actualclass[cls][meth])
	res = pg.actualclass[cls][meth](*args,**kwargs)
	return res

def DoRemoteClassInit(cls, meth, clsdef, *args, **kwargs):
	print('Class init for {}.{} with {} {} {}'.format(cls, meth, clsdef, args, kwargs))
	tmp1 = clsdef(*args,**kwargs)
	print(tmp1)
	print(tmp1.actualobj)


class remotestuff(object):
	remclass = {}
	actualclass = {}

	def __init__(self):
		pgclasses = pgactual.__dict__
		for nm, desc in pgclasses.items():
			if inspect.isclass(desc):
				subcls = desc.__dict__
				actualmethods = {}
				remmethods = {'__module__': 'guicore.screencallmanager'}
				for methnm, methcod in subcls.items():
					if methnm == '__init__':
						remmethods['__init__'] = functools.partial(DoRemoteClassInit, nm, methnm, desc)
						remmethods['dohook'] = functools.partial(DoRemoteCall, nm, 'dohook', desc)
					elif inspect.isfunction(methcod):
						remmethods[methnm] = functools.partial(DoRemoteCall, nm, methnm)
						actualmethods[methnm] = methcod
					elif type(methcod) == staticmethod:
						remmethods[methnm] = functools.partial(DoRemoteCallStatic, nm, methnm)
						actualmethods[methnm] = methcod.__func__
				self.remclass[nm] = type(nm, (object,), remmethods)
				self.actualclass[nm] = actualmethods
		print(self.remclass)
		print(self.actualclass)
		for xx,zz in self.actualclass.items():
			print('{}: {}'.format(xx,zz))
		self.remotes = type('remotes', (object,), self.remclass)


#global x
pg = remotestuff()
pg.__dict__ = pg.remclass
print(pg.__dict__['Surface'])
'''
