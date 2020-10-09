# adapted from pimoroni evdev support for the 7 inch capacitive screen
# added support for the resistive 3.5 and maybe others that doesn't depend upon SDL 1.2
import errno
import glob
import io
import os
import queue
import struct
import time
from collections import namedtuple
import logsupport


import select

import debug

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
		return self.x, self.y

	@property
	def last_position(self):
		return self.last_x, self.last_y

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
				# with (open('templog', 'a')) as f:
				#	f.write('{} {} {}\n'.format(self.x, self.y, self.slot))
				#	f.flush()

				self.on_press(event, self)
			if event == TS_RELEASE and callable(self.on_release):
				self.on_release(event, self)

		self.events = []


class Touches(list):
	@property
	def valid(self):
		return [tch for tch in self if tch.valid]


class Touchscreen(object):
	EVENT_FORMAT = str('llHHi')
	EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

	def __init__(self, configdir, touchmod):
		self.touchdefs = {}
		self.touchmod = touchmod
		with open('touchdefinitions') as f:
			defs = f.read().splitlines()
			for l in defs:
				touchitem = l.split('|')
				self.touchdefs[touchitem[0]] = touchitem[1:]
		try:
			with open(configdir + '/touchdefinitions') as f:
				defs = f.read().splitlines()
				for l in defs:
					touchitem = l.split('|')
					self.touchdefs[touchitem[0]] = touchitem[1:]
		except:
			pass

		self._use_multitouch = True
		self.controller = "unknown"
		self._shiftx = 0
		self._shifty = 0
		self._flipx = 0  # 0 for ok else size of x from which to subtract touch value
		self._flipy = 0  # 0 for ok else size of y from which to subtract touch value
		self._scalex = 1.0
		self._scaley = 1.0
		self._capscreen = True
		self.a = None
		self._running = False
		self._thread = None
		self._f_poll = select.poll()
		self._f_device = io.open(self._touch_device(), 'rb', self.EVENT_SIZE)
		self._f_poll.register(self._f_device, select.POLLIN)
		self.position = Touch(0, 0, 0)
		self.touches = Touches([Touch(x, 0, 0) for x in range(10)])
		self._event_queue = queue.Queue()
		self._touch_slot = 0

	def _run(self):
		self._running = True
		while self._running:
			self.poll()
			time.sleep(0.00001)

	def run(self):
		self._run()

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
			(tv_sec, tv_usec, ttype, code, value) = struct.unpack(self.EVENT_FORMAT, event)
			self._event_queue.put(TouchEvent(tv_sec + (tv_usec / 1000000), ttype, code, value))

	def _wait_for_events(self, timeout=2):
		return self._f_poll.poll(timeout)

	def poll(self):
		self._get_pending_events()

		while not self._event_queue.empty():
			event = self._event_queue.get()
			debug.debugPrint('LLTouch', 'Touch: ' + str(event))
			self._event_queue.task_done()

			if event.type == EV_SYN:  # Sync
				for tch in self.touches:
					tch.handle_events()
				return self.touches

			if event.type == EV_KEY and not self._capscreen:
				if event.code == BTN_TOUCH:
					self._touch_slot = 0
					# self._current_touch.id = 1
					if self.a is None:
						self._current_touch.x = self.position.x
						self._current_touch.y = self.position.y
					else:
						self._current_touch.x = (self.a[2] + self.a[0] * self.position.x + self.a[
							1] * self.position.y) / self.a[6]
						self._current_touch.y = (self.a[5] + self.a[3] * self.position.x + self.a[
							4] * self.position.y) / self.a[6]
					if self._flipx != 0:
						self._current_touch.x = self._flipx - self._current_touch.x
					if self._flipy != 0:
						self._current_touch.y = self._flipy - self._current_touch.y
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
					tmp = event.value + self._shiftx
					if self._flipx != 0:
						tmp = self._flipx - event.value
					if tmp < 0:
						logsupport.Logs.Log('Negative touch position(x): {}'.format(tmp),
											severity=logsupport.ConsoleWarning)
						tmp = 0
					self._current_touch.x = round(tmp * self._scalex)

				if event.code == ABS_MT_POSITION_Y:
					tmp = event.value + self._shifty
					if self._flipy != 0:
						tmp = self._flipy - event.value
					if tmp < 0:
						logsupport.Logs.Log('Negative touch position(y): {}'.format(tmp),
											severity=logsupport.ConsoleWarning)
						tmp = 0
					self._current_touch.y = round(tmp * self._scaley)

				if event.code == ABS_X:
					self.position.x = event.value

				if event.code == ABS_Y:
					self.position.y = event.value

		return []

	def _touch_device(self):
		global ABS_MT_POSITION_Y, ABS_MT_POSITION_X
		# return '/dev/input/touchscreen'
		for evdev in glob.glob("/sys/class/input/event*"):
			try:
				with io.open(os.path.join(evdev, 'device', 'name'), 'r') as f:
					dev = f.read().strip()
					if self.touchmod != '':
						dev = dev + '.' + self.touchmod
					if dev in self.touchdefs:
						self.controller = dev
						vals = self.touchdefs[dev]
						self._shiftx = int(vals[1])
						self._shifty = int(vals[2])
						self._flipx = int(vals[3])
						self._flipy = int(vals[4])
						self._scalex = float(vals[5])
						self._scaley = float(vals[6])
						if len(vals) > 7:
							self._swapaxes = vals[7] in ('True', '1', 'true', 'TRUE')
						else:
							self._swapaxes = False

						if self._swapaxes:
							tmp = ABS_MT_POSITION_X
							ABS_MT_POSITION_X = ABS_MT_POSITION_Y
							ABS_MT_POSITION_Y = tmp

						self._capscreen = vals[0] in ('True', '1', 'true', 'TRUE')
						if not self._capscreen:
							with open('/etc/pointercal', 'r') as pc:
								self.a = list(int(x) for x in next(pc).split())
						return os.path.join('/dev', 'input', os.path.basename(evdev))

			except IOError as e:
				if e.errno != errno.ENOENT:
					raise
		raise RuntimeError('Unable to locate touchscreen device')

	def read(self):
		return next(iter(self))


'''
if __name__ == "__main__":
	import signal

	pygame.init()
	pygame.fastevent.init()
	a = [5724, -6, -1330074, 26, 8427, -1034528, 65536]
	b = [34, 952, 38, 943]

	ts = Touchscreen()


	def handle_event(event, tch):
		#xx = (a[2] + a[0] * touch.x + a[1] * touch.y) / a[6]
		#yy = (a[5] + a[3] * touch.x + a[4] * touch.y) / a[6]
		#Xx = (touch.x - b[0]) * 320 / (b[1] - b[0])
		#Xy = (touch.y - b[2]) * 480 / (b[3] - b[2])
		print(["Release", "Press", "Move"][event],
			  tch.slot,
			  tch.x,
			  tch.y)
		return
		# noinspection PyUnreachableCode
		if event == 1:
			e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (tch.x, tch.y)})
			pygame.fastevent.post(e)
		elif event == 0:
			e = pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (tch.x, tch.y)})
			pygame.fastevent.post(e)


	for touch in ts.touches:
		touch.on_press = handle_event
		touch.on_release = handle_event
		touch.on_move = handle_event

#	ts.run()

	try:
		signal.pause()
	except KeyboardInterrupt:
		print("Stopping thread...")
		ts.stop()
		exit()
'''
