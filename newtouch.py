# adapted from pimoroni evdev support for the 7 inch capacitive screen
# added support for the resistive 3.5 and maybe others that doesn't depend upon SDL 1.2

import glob
import io
import os
import errno
import struct
from collections import namedtuple
import threading
import time
import select
import Queue
import pygame

TOUCH_X = 0
TOUCH_Y = 1

TouchEvent = namedtuple('TouchEvent', ('timestamp', 'type', 'code', 'value'))

EV_SYN = 0
EV_ABS = 3

ABS_X = 0
ABS_Y = 1

EV_KEY = 1
BTN_TOUCH = 330
ABS_MT_SLOT = 0x2f  # 47 MT slot being modified
ABS_MT_POSITION_X = 0x35  # 53 Center X of multi touch position
ABS_MT_POSITION_Y = 0x36  # 54 Center Y of multi touch position
ABS_MT_TRACKING_ID = 0x39  # 57 Unique ID of initiated contact

TS_PRESS = 1
TS_RELEASE = 0
TS_MOVE = 2


class Touch(object):
	def __init__(self, slot, x, y):
		self.slot = slot

		self._x = x
		self._y = y
		self.last_x = -1
		self.last_y = -1

		self._id = -1
		self.events = []
		self.on_move = None
		self.on_press = None
		self.on_release = None

	@property
	def position(self):
		return (self.x, self.y)

	@property
	def last_position(self):
		return (self.last_x, self.last_y)

	@property
	def valid(self):
		return self.id > -1

	@property
	def id(self):
		return self._id

	@id.setter
	def id(self, value):
		if value != self._id:
			if value == -1 and not TS_RELEASE in self.events:
				self.events.append(TS_RELEASE)
			elif not TS_PRESS in self.events:
				self.events.append(TS_PRESS)

		self._id = value

	@property
	def x(self):
		return self._x

	@x.setter
	def x(self, value):
		if value != self._x and not TS_MOVE in self.events:
			self.events.append(TS_MOVE)
		self.last_x = self._x
		self._x = value

	@property
	def y(self):
		return self._y

	@y.setter
	def y(self, value):
		if value != self._y and not TS_MOVE in self.events:
			self.events.append(TS_MOVE)
		self.last_y = self._y
		self._y = value

	def handle_events(self):
		"""Run outstanding press/release/move events"""
		for event in self.events:
			if event == TS_MOVE and callable(self.on_move):
				self.on_move(event, self)
			if event == TS_PRESS and callable(self.on_press):
				self.on_press(event, self)
			if event == TS_RELEASE and callable(self.on_release):
				self.on_release(event, self)

		self.events = []


class Touches(list):
	@property
	def valid(self):
		return [touch for touch in self if touch.valid]


class Touchscreen(object):
	TOUCHSCREEN_EVDEV_NAME = 'FT5406 memory based driver'
	TOUCHSCREEN_RESISTIVE = 'stmpe-ts'
	EVENT_FORMAT = str('llHHi')
	EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

	def __init__(self):
		self.a = None
		self._running = False
		self._thread = None
		self._f_poll = select.poll()
		self._f_device = io.open(self._touch_device(), 'rb', self.EVENT_SIZE)
		self._f_poll.register(self._f_device, select.POLLIN)
		self.position = Touch(0, 0, 0)
		self.touches = Touches([Touch(x, 0, 0) for x in range(10)])
		self._event_queue = Queue.Queue()
		self._touch_slot = 0


	def _run(self):
		self._running = True
		while self._running:
			self.poll()

	# time.sleep(0.0001)

	def run(self):
		if self._thread is not None:
			return

		self._thread = threading.Thread(target=self._run)
		self._thread.setDaemon(True)
		self._thread.start()

	def stop(self):
		if self._thread is None:
			return

		self._running = False
		self._thread.join()
		self._thread = None

	@property
	def _current_touch(self):
		return self.touches[self._touch_slot]

	def close(self):
		self._f_device.close()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, exc_tb):
		self.close()

	def __iter__(self):
		pass

	def _lazy_read(self):
		while self._wait_for_events():
			event = self._f_device.read(self.EVENT_SIZE)
			if not event:
				break
			yield event

	def _get_pending_events(self):
		for event in self._lazy_read():
			(tv_sec, tv_usec, type, code, value) = struct.unpack(self.EVENT_FORMAT, event)
			self._event_queue.put(TouchEvent(tv_sec + (tv_usec / 1000000), type, code, value))

	def _wait_for_events(self, timeout=2):
		return self._f_poll.poll(timeout)

	def poll(self):
		self._get_pending_events()

		while not self._event_queue.empty():
			event = self._event_queue.get()
			print(event) #todo delete
			self._event_queue.task_done()

			if event.type == EV_SYN:  # Sync
				for touch in self.touches:
					touch.handle_events()
				return self.touches

			if event.type == EV_KEY:
				if event.code == BTN_TOUCH:
					self._touch_slot = 0
					# self._current_touch.id = 1
					if a is None:
						self._current_touch.x = self.position.x
						self._current_touch.y = self.position.y
					else:
						self._current_touch.x = (a[2] + a[0] * self.position.x + a[1] * self.position.y) / a[6]
						self._current_touch.y = (a[5] + a[3] * self.position.x + a[4] * self.position.y) / a[6]
					if event.value == 1:
						self._current_touch.events.append(TS_PRESS)
					else:
						self._current_touch.events.append(TS_RELEASE)

			if event.type == EV_ABS:  # Absolute cursor position
				if event.code == ABS_MT_SLOT:
					self._touch_slot = event.value

				if event.code == ABS_MT_TRACKING_ID:
					self._current_touch.id = event.value

				if event.code == ABS_MT_POSITION_X:
					self._current_touch.x = event.value

				if event.code == ABS_MT_POSITION_Y:
					self._current_touch.y = event.value

				if event.code == ABS_X:
					self.position.x = event.value

				if event.code == ABS_Y:
					self.position.y = event.value

		return []

	def _touch_device(self):
		#return '/dev/input/touchscreen'
		for evdev in glob.glob("/sys/class/input/event*"):
			try:
				with io.open(os.path.join(evdev, 'device', 'name'), 'r') as f:
					dev = f.read().strip()
					if dev == self.TOUCHSCREEN_EVDEV_NAME:
						return os.path.join('/dev', 'input', os.path.basename(evdev))
					elif dev == self.TOUCHSCREEN_RESISTIVE:
						with open('/etc/pointercal','r') as pc:
							self.a = list(int(x) for x in next(pc).split())
						# set to do corrections? TODO read pointercal and set a flag to correct
						return os.path.join('/dev', 'input', os.path.basename(evdev))
			except IOError as e:
				if e.errno != errno.ENOENT:
					raise
		raise RuntimeError('Unable to locate touchscreen device')

	def read(self):
		return next(iter(self))


if __name__ == "__main__":
	import signal

	pygame.init()
	pygame.fastevent.init()
	a = [5724, -6, -1330074, 26, 8427, -1034528, 65536]
	b = [34, 952, 38, 943]

	ts = Touchscreen()


	def handle_event(event, touch):
		#xx = (a[2] + a[0] * touch.x + a[1] * touch.y) / a[6]
		#yy = (a[5] + a[3] * touch.x + a[4] * touch.y) / a[6]
		#Xx = (touch.x - b[0]) * 320 / (b[1] - b[0])
		#Xy = (touch.y - b[2]) * 480 / (b[3] - b[2])
		print(["Release", "Press", "Move"][event],
		      touch.slot,
		      touch.x,
		      touch.y)
		return
		if event == 1:
			e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (touch.x, touch.y)})
			pygame.fastevent.post(e)
		elif event == 0:
			e = pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (touch.x, touch.y)})
			pygame.fastevent.post(e)


	for touch in ts.touches:
		touch.on_press = handle_event
		touch.on_release = handle_event
		touch.on_move = handle_event

	ts.run()

	try:
		signal.pause()
	except KeyboardInterrupt:
		print("Stopping thread...")
		ts.stop()
		exit()
