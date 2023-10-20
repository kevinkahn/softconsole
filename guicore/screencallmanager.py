import pygame
from pygame import gfxdraw
import inspect
import sys
import functools


class pg(object):
	FULLSCREEN = pygame.FULLSCREEN
	Rect = pygame.Rect

	class display(object):
		def __init__(self):
			pass

		@staticmethod
		def init():
			return pygame.display.init()

		@staticmethod
		def quit():
			return pygame.display.quit()

		@staticmethod
		def set_mode(*args, **kwargs):
			return pg.Surface(wrap=pygame.display.set_mode(*args, **kwargs))

		@staticmethod
		def update(*args, **kwargs):
			return pygame.display.update(*args, **kwargs)

		@staticmethod
		def Info():
			return pygame.display.Info()

	class Surface(object):
		z = None

		def __init__(self, *args, **kwargs):
			if 'wrap' in kwargs:
				# print('Wrap {} -> {}'.format(kwargs['wrap'],self))
				self.z = kwargs['wrap']
			else:
				self.z = pygame.Surface(*args, **kwargs)

		def blit(self, *args, **kwargs):
			# print('Blit {}'.format(args))
			tmpargs = list(args)
			tmpargs[0] = self._unwrap(tmpargs[0])
			return self.z.blit(*tmpargs, **kwargs)

		def convert_alpha(self, *args):
			tmpargs = list(args)
			if len(args) > 0:
				tmpargs[0] = self._unwrap(tmpargs[0])
				return self.z.convert_alpha(*tmpargs)
			else:
				return pg.Surface(wrap=self.z.convert_alpha())

		def set_colorkey(self, *args, **kwargs):
			return self.z.set_colorkey(*args, **kwargs)

		def get_colorkey(self):
			return self.z.get_colorkey()

		def fill(self, *args, **kwargs):
			return self.z.fill(*args, **kwargs)

		def get_height(self):
			return self.z.get_height()

		def get_width(self):
			return self.z.get_width()

		def set_alpha(self, *args, **kwargs):
			return self.z.set_alpha(*args, **kwargs)

		def _unwrap(self, target):
			# print('Unwrap {} -> {}'.format(target, target.z))
			return target.z

		def get_locked(self):
			return self.z.get_locked()

	class mouse(object):
		@staticmethod
		def set_visible(*args, **kwargs):
			return pygame.mouse.set_visible(*args, **kwargs)

	class transform(object):
		@staticmethod
		def smoothscale(*args, **kwargs):
			return pg.Surface(wrap=pygame.transform.smoothscale(*_unwrapSurf(*args), **kwargs))

		@staticmethod
		def rotate(*args, **kwargs):
			return pg.Surface(wrap=pygame.transform.rotate(*_unwrapSurf(*args), **kwargs))

	class image(object):
		@staticmethod
		def load(*args, **kwargs):
			return pg.Surface(wrap=pygame.image.load(*args, **kwargs))

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
			z = None

			def __init__(self, item):
				self.z = item

			def render(self, *args, **kwargs):
				return pg.Surface(wrap=self.z.render(*args, **kwargs))

			def size(self, *args, **kwargs):
				return self.z.size(*args, **kwargs)

			def get_linesize(self, *args, **kwargs):
				return self.z.get_linesize(*args, **kwargs)

		@staticmethod
		def init():
			return pygame.font.init()

		@staticmethod
		def get_fonts():
			return pygame.font.get_fonts()

		@staticmethod
		def SysFont(*args, **kwargs):
			y = pygame.font.SysFont(*args, **kwargs)
			return pg.font.Font(y)

	def init():
		return pygame.init()

	def quit():
		return pygame.quit()


def _unwrapSurf(*args):
	tempargs = list(args)
	tempargs[0] = tempargs[0]._unwrap(tempargs[0])
	return tempargs


def DoRemoteCall(cls, meth, params, keywdparams):
	print('Issue call for {}.{} with {},{}'.format(cls, meth, params, keywdparams))


class remotestuff(object):
	remclass = {}

	def __init__(self):
		pgclasses = pg.__dict__
		# remclass = {}
		for nm, desc in pgclasses.items():
			if inspect.isclass(desc):
				subcls = desc.__dict__
				remmethods = {'__module--': 'guicore.screencallmanager'}
				for methnm, methcod in subcls.items():
					if inspect.isfunction(methcod):
						remmethods[methnm] = functools.partial(DoRemoteCall, nm, methnm)
					elif type(methcod) == staticmethod:
						remmethods[methnm] = functools.partial(DoRemoteCall, nm, methnm)
				self.remclass[nm] = type(nm, (object,), remmethods)
		print(self.remclass)
		self.remotes = type('remotes', (object,), self.remclass)


global x
x = remotestuff()
x.__dict__ = x.remclass
