import time
from threading import Thread, Event


class RepeatingTimer(Thread):
	"""Call a function after a specified number of seconds:

			t = Timer(30.0, f, args=None, kwargs=None)
			t.start()
			t.cancel()     # stop the timer's action if it's still waiting

	"""

	def __init__(self, interval, function, name='', args=None, kwargs=None):
		Thread.__init__(self, name=name)
		self.interval = interval
		self.function = function

		self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.finished = Event()
		self.running = Event()
		self.running.set()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.running.set()

	def resume(self):
		self.running.set()

	def pause(self):
		self.running.clear()

	def run(self):
		while not self.finished.wait(self.interval):
			if self.running.is_set():
				self.function()
			else:
				self.running.wait()


'''
	def run(self):
		self.finished.wait(self.interval)
		if not self.finished.is_set():
			self.function(*self.args, **self.kwargs)
		self.finished.set()

	def run(self):
		while not self.finished.wait(self.interval):
			self.function(*self.args, **self.kwargs)
			
'''


def testfn():
	print('Tick')


t = RepeatingTimer(1, testfn, name='TestTimer')

print('{} Starting'.format(time.time()))
t.start()
time.sleep(5)
print('{} pause'.format(time.time()))
t.pause()
time.sleep(3)
print('{} resume'.format(time.time()))
t.resume()
time.sleep(5)
# print('{} pause'.format(time.time()))
# t.pause()
print('{} cancel'.format(time.time()))
t.cancel()
time.sleep(3)
print('Thread {} alive {}'.format(t.name, t.is_alive()))

"""
interval = .5
nowtime = time.time()

'''
while True:
	time.sleep(interval)
	postsleep = time.time()
	delta = postsleep - nowtime
	if delta > interval * 1.2:
		print('Now: {} PostSleep: {} Delta: {}'.format(nowtime, postsleep, delta))
	nowtime = time.time()

print('Ending')
'''

import pygame
pygame.init()
pygame.fastevent.init()

evnt = pygame.event.Event(pygame.USEREVENT,{})

timer = threading.Timer(10.0, print, 'test')


pygame.time.set_timer(evnt.type, 2)

while True:
	ev = pygame.fastevent.wait()
	postwait = time.time()
	delta = postwait - nowtime
	if delta > 2.2:
		print('Now: {} PostSleep: {} Delta: {}'.format(nowtime, postwait, delta))
	nowtime = time.time()
	pygame.time.set_timer(evnt.type, 2)
"""
