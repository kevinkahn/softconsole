import pygame
import pygame.gfxdraw

"""
To disable the thread version of pygame uncomment the below and comment the rest of the file

pg = pygame
pg.gfxdraw = pygame.gfxdraw
"""

import time

from collections import deque
import threading
import queue

callhist = deque('', 20)


def remote(func, *args, **kwargs):
	if kwargs != {}:
		print('KEYWORDS! {}'.format(kwargs))
	return Send(rem, None, func, args, kwargs)


def remoteobj(obj, func, *args, **kwargs):
	return Send(remobj, obj, func, args, kwargs)


class pg(object):
	FULLSCREEN = pygame.FULLSCREEN
	Rect = pygame.Rect

	class display(object):

		@staticmethod
		def init():
			return remote('display.init')

		@staticmethod
		def quit():
			return remote('display.quit')

		@staticmethod
		def set_mode(*args, **kwargs):
			return pg.Surface(wrap=remote('display.set_mode', *args, **kwargs))

		@staticmethod
		def update(*args, **kwargs):
			return remote('display.update', *args, **kwargs)

		@staticmethod
		def Info():
			return remote('display.Info')

	class Surface(object):
		actualobj = None

		def __init__(self, *args, **kwargs):
			if 'wrap' in kwargs:
				# print('Wrap {} -> {}'.format(kwargs['wrap'],self))
				self.actualobj = kwargs['wrap']
			else:
				self.actualobj = remote('Surface', *args, **kwargs)

		def blit(self, *args, **kwargs):
			# print('Blit {}'.format(args))
			tmpargs = list(args)
			tmpargs[0] = self._unwrap(tmpargs[0])
			return remoteobj(self.actualobj, 'blit', *tmpargs, **kwargs)

		def convert_alpha(self, *args):
			tmpargs = list(args)
			if len(args) > 0:
				tmpargs[0] = self._unwrap(tmpargs[0])
				return remoteobj(self.actualobj, 'convert_alpha', *tmpargs)
			else:
				return pg.Surface(wrap=remoteobj(self.actualobj, 'convert_alpha'))

		def set_colorkey(self, *args, **kwargs):
			return remoteobj(self.actualobj, 'set_colorkey', *args, **kwargs)

		def get_colorkey(self):
			return remoteobj(self.actualobj, 'get_colorkey')

		def fill(self, *args, **kwargs):
			return remoteobj(self.actualobj, 'fill', *args, **kwargs)

		def get_height(self):
			return remoteobj(self.actualobj, 'get_height')

		def get_width(self):
			return remoteobj(self.actualobj, 'get_width')

		def set_alpha(self, *args, **kwargs):
			return remoteobj(self.actualobj, 'set_alpha', *args, **kwargs)

		def _unwrap(self, target):
			# print('Unwrap {} -> {}'.format(target, target.actualobj))
			return target.actualobj

		def get_locked(self):
			return remoteobj(self.actualobj, 'get_locked')

	class mouse(object):
		@staticmethod
		def set_visible(*args, **kwargs):
			return remote('mouse.set_visible', *args, **kwargs)

	class transform(object):  # Memoryless so do locally
		@staticmethod
		def smoothscale(*args, **kwargs):
			return pg.Surface(wrap=pygame.transform.smoothscale(*_unwrapSurf(*args), **kwargs))

		@staticmethod
		def rotate(*args, **kwargs):  # Memoryless so do locally
			return pg.Surface(wrap=pygame.transform.rotate(*_unwrapSurf(*args), **kwargs))

	class image(object):  # Memoryless so do locally
		@staticmethod
		def load(*args, **kwargs):  # Memoryless so do locally
			return pg.Surface(wrap=pygame.image.load(*args, **kwargs))

		@staticmethod
		def save(*args, **kwargs):  # Memoryless so do locally
			pygame.image.save(*_unwrapSurf(*args), **kwargs)

	class draw(object):

		@staticmethod
		def line(*args, **kwargs):
			return remote('draw.line', *_unwrapSurf(*args), **kwargs)

		@staticmethod
		def lines(*args, **kwargs):
			return remote('draw.lines', *_unwrapSurf(*args), **kwargs)

		@staticmethod
		def polygon(*args, **kwargs):
			return remote('draw.polygon', *_unwrapSurf(*args), **kwargs)

		@staticmethod
		def rect(*args, **kwargs):
			return remote('draw.rect', *_unwrapSurf(*args), **kwargs)

		@staticmethod
		def circle(*args, **kwargs):
			return remote('draw.circle', *_unwrapSurf(*args), **kwargs)

	class gfxdraw(object):
		@staticmethod
		def filled_trigon(*args, **kwargs):
			return remote('gfxdraw.filled_trigon', *_unwrapSurf(*args), **kwargs)

	'''
	# class Rect(object):
	# this is tricky to wrap but may not need to be unless other functions are called in it
	#	z = None
	#	def __init__(self, *args):
	#		self.z = pygame.Rect(*args)
	'''

	class font(object):

		class Font(object):
			actualobj = None

			def __init__(self, item):
				self.actualobj = item

			def render(self, *args, **kwargs):
				return pg.Surface(wrap=remoteobj(self.actualobj, 'render', *args, **kwargs))

			def size(self, *args, **kwargs):
				return remoteobj(self.actualobj, 'size', *args, **kwargs)

			def get_linesize(self, *args, **kwargs):
				return remoteobj(self.actualobj, 'get_linesize', *args, **kwargs)

		@staticmethod
		def init():
			return remote('font.init')

		@staticmethod
		def get_fonts():
			return remote('font.get_fonts')

		@staticmethod
		def SysFont(*args, **kwargs):
			y = pygame.font.SysFont(*args, **kwargs)
			return pg.font.Font(y)
	# could be tricky - wants to return a Font - may need to do wrap of some sort, also think about Font _init

	@staticmethod
	def init():
		return remote('init')

	@staticmethod
	def quit():
		return remote('quit')


def _unwrapSurf(*args):
	tempargs = list(args)
	tempargs[0] = tempargs[0]._unwrap(tempargs[0])
	return tempargs


ToPygame = queue.SimpleQueue()
FromPygame = {}
SeqNums = {}
SeqNumLast = {}

initq = 0
rem = 1
remobj = 2


def Send(calltype, obj, func, args, kwargs):
	me = threading.current_thread().name
	if me not in FromPygame:
		ToPygame.put([(me, -1), 0])
		while me not in FromPygame:
			time.sleep(.1)
		FromPygame[me].get()

	SeqNums[me] = (SeqNums[me] + 1) % 10000000
	if calltype == rem:
		callparmsout = [(me, SeqNums[me]), calltype, func, args, kwargs]
	else:
		callparmsout = [(me, SeqNums[me]), calltype, obj, func, args, kwargs]
	callhist.append('Call: {}'.format(callparmsout))

	ToPygame.put(callparmsout)
	resout = FromPygame[me].get()
	if SeqNums[me] != resout[0][1]:
		print('SEQ Error: {}:{} <> {}'.format(me, SeqNums[me], resout[0]))
		print('SEQ Error: {}:{} <> {}'.format(me, SeqNums[me], resout[0]),
			  file=open('/home/pi/Console/pgerrors.txt', 'a'))
		# callparmsout = [(me, SeqNums[me]), errrpt, resout[0], callhist]
		# ToPygame.put(callparmsout)
		for i in callhist:
			print(i)
			print(i, file=open('/home/pi/Console/pgerrors.txt', 'a'))
	return resout[1]


def DoPygameOps():
	try:
		while True:
			callparms = ToPygame.get()

			callhist.append('Exec: {}'.format(callparms))
			if callparms[1] == rem:
				op = callparms[2].split('.')
				fn = pygame
				for i in op:
					fn = fn.__dict__[i]
				res = fn(*callparms[3], **callparms[4])
			elif callparms[1] == remobj:
				obj = callparms[2]
				func = callparms[3]
				res = obj.__class__.__dict__[func](obj, *callparms[4], **callparms[5])
			else:
				SeqNums[callparms[0][0]] = 0
				SeqNumLast[callparms[0][0]] = 0
				FromPygame[callparms[0][0]] = queue.SimpleQueue()
				res = 'ok'

			FromPygame[callparms[0][0]].put((callparms[0], res))
	except Exception as E:
		print('Pygame Thread excetion {}'.format(E))


PyGameExec = threading.Thread(target=DoPygameOps, name='PyGame call thread')
PyGameExec.start()
