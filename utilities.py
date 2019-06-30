import collections
import os
import signal

import pygame

import config
import debug
import hw
import logsupport
import threadmanager  # should not depend on in project files - move somewhere else
from controlevents import CEvent, PostEvent, ConsoleEvent
from logsupport import ConsoleDetail

# from sets import Set

globdoc = {}
moddoc = {}
paramlog = []
exemplarobjs = collections.OrderedDict()

evntcnt = 0
lastup = 0
previousup = 0

ts = None


# next several lines stolen from https://stackoverflow.com/questions/39198961/pygame-init-fails-when-run-with-systemd
# this handles some weird random SIGHUP when initializing pygame, it's really a hack to work around it
# Not really sure what other ill effects this might have!!!
def handler(signum, frame):
	logsupport.DevPrint('Systemd signal hack raised {} {}'.format(signum, repr(frame)))
	pass


try:
	signal.signal(signal.SIGHUP, handler)
except AttributeError:
	# Windows compatibility
	pass


# end SIGHUP hack


class clsstruct:
	def __init__(self, nm):
		self.name = nm
		self.members = []
		self.membernms = set()

	def addmem(self, nm):
		self.membernms.add(nm)


clslst = {}
doclst = {}


def register_example(estr, obj):
	exemplarobjs[estr] = list(dir(obj))
	mro = list(obj.__class__.__mro__)
	mro.reverse()
	for i in range(len(mro)):
		t = mro[i]
		if t.__name__ not in clslst:
			doclst[t.__name__] = t.__doc__
			clslst[t.__name__] = clsstruct(t.__name__)
		for e in mro[i + 1:]:
			clslst[t.__name__].addmem(e.__name__)


def LogParams():
	global paramlog
	for p in paramlog:
		logsupport.Logs.Log(p, severity=ConsoleDetail)


def InitializeEnvironment():
	# this section is an unbelievable nasty hack - for some reason Pygame
	# needs a keyboardinterrupt to initialise in some limited circs (second time running)
	# lines below commented with HACK also part of workaround
	# see https://stackoverflow.com/questions/17035699/pygame-requires-keyboard-interrupt-to-init-display
	global lastup, previousup, ts
	class Alarm(Exception):
		pass

	def alarm_handler(signum, frame):
		print('Hack alarm raised', signum, repr(frame))
		raise Alarm

	# end hack
	try:
		with open("{}/.Screentype".format(config.sysStore.HomeDir)) as f:
			scrntyp = f.readline().rstrip('\n')
	except IOError:
		scrntyp = "*Unknown*"

	hw.initOS(scrntyp, os.path.dirname(config.sysStore.configfile))

	config.sysStore.SetVal('PersonalSystem',os.path.isfile(config.sysStore.HomeDir + "/homesystem"))

	# todo move touchhandler selection to hw - return the handler to start for the thread

	from touchhandler import Touchscreen, TS_PRESS, TS_RELEASE, TS_MOVE
	ts = Touchscreen(os.path.dirname(config.sysStore.configfile))

	def touchhandler(event, touch):
		global evntcnt
		evntcnt += 1
		slot = touch.slot
		if slot != 0: return  # no multitouch events for now
		p = (touch.x, touch.y)
		if event == TS_PRESS:
			debug.debugPrint('Touch', 'Press pos: {} seq: {}'.format(p, evntcnt))
			PostEvent(ConsoleEvent(CEvent.MouseDown, pos=p, seq=evntcnt))  # eventfix
		elif event == TS_RELEASE:
			debug.debugPrint('Touch', 'Repease pos: {} seq: {}'.format(p, evntcnt))
			PostEvent(ConsoleEvent(CEvent.MouseUp, pos=p, seq=evntcnt))
		elif event == TS_MOVE:
			debug.debugPrint('Touch', 'Motion pos: {} seq: {}'.format(p, evntcnt))
			PostEvent(ConsoleEvent(CEvent.MouseMotion, pos=p, seq=evntcnt))

	for touchtyp in ts.touches:
		touchtyp.on_press = touchhandler
		touchtyp.on_release = touchhandler
		touchtyp.on_move = touchhandler

	threadmanager.SetUpHelperThread('TouchHandler', ts.run)

	try:
		lastup = os.path.getmtime("{}/.ConsoleStart".format(config.sysStore.HomeDir))
		with open("{}/.ConsoleStart".format(config.sysStore.HomeDir)) as f:
			laststart = float(f.readline())
			lastrealstart = float(f.readline())
		previousup = lastup - lastrealstart
		prevsetup = lastrealstart - laststart
	except (IOError, ValueError):
		previousup = -1
		lastup = -1
		prevsetup = -1

	with open("{}/.RelLog".format(config.sysStore.HomeDir), "a") as f:
		f.write(
			str(config.sysStore.ConsoleStartTime) + ' ' + str(prevsetup) + ' ' + str(previousup) + ' ' + str(lastup) + ' '
			+ str(config.sysStore.ConsoleStartTime - lastup) + '\n')

	signal.signal(signal.SIGALRM, alarm_handler)  # HACK
	signal.alarm(3)  # HACK
	try:  # HACK
		hw.screen = pygame.display.set_mode((hw.screenwidth, hw.screenheight),
											pygame.FULLSCREEN)  # real needed line
		signal.alarm(0)  # HACK
	except Alarm:  # HACK
		raise KeyboardInterrupt  # HACK

	hw.screen.fill((0, 0, 0))  # clear screen
	pygame.display.update()
	pygame.mouse.set_visible(False)  # no cursor


def DumpDocumentation():
	docfile = open('docs/params.txt', 'w')
	os.chmod('docs/params.txt', 0o555)
	docfile.write('Global Parameters:\n')
	for p in sorted(globdoc):
		docfile.write(
			'    {:32s}:  {:8s}  {}\n'.format(p, globdoc[p][0].__name__, str(globdoc[p][1])))
	docfile.write('Module Parameters:\n')
	for p in sorted(moddoc):
		docfile.write('    ' + p + '\n')
		docfile.write('        Local Parameters:\n')
		for q in sorted(moddoc[p]['loc']):
			docfile.write('            {:24s}:  {:8s}\n'.format(q, moddoc[p]['loc'][q].__name__))
		docfile.write('        Overrideable Globals:\n')
		for q in sorted(moddoc[p]['ovrd']):
			docfile.write('            ' + q + '\n')
	docfile.close()
	docfile = open('docs/classstruct.txt', 'w')
	docfile.write('Class/Attribute Structure:\n')
	docfile.write('\n')
	mdfile = open('docs/classstruct.md', 'w')
	mdfile.write('# Class/Attribute Structure:\n')
	mdfile.write('\n')

	varsinuse = {}
	olditems = []
	for i, scr in exemplarobjs.items():
		varsinuse[i] = [x for x in scr if not x.startswith('_') and x not in olditems]
		olditems += [x for x in scr if not x.startswith('_')]

	def scrublowers(ritem):
		lower = []
		rtn = list(ritem.members)
		for mem in ritem.members:
			lower += scrublowers(mem)
		ritem.members = [xitem for xitem in ritem.members if xitem not in lower]
		return rtn

	def docwrite(ritem, ind, md):
		docfile.write(ind + ritem.name + ': [' + ', '.join([n2.name for n2 in ritem.members]) + ']\n')
		mdfile.write('\n' + md + ritem.name + ': [' + ', '.join([n2.name for n2 in ritem.members]) + ']\n')
		docfile.write(ind + (doclst[ritem.name] if not doclst[ritem.name] is None else "***missing***") + '\n')
		mdfile.write((doclst[ritem.name] if not doclst[ritem.name] is None else "\n***missing***\n") + '\n')
		if ritem.name in varsinuse:
			for v in varsinuse[ritem.name]:
				docfile.write(ind + '  ' + v + '\n')
				mdfile.write('*  ' + v + '\n')
		for mem in ritem.members:
			docwrite(mem, ind + '    ', '##')

	for c in clslst.values():
		for n in c.membernms:
			c.members.append(clslst[n])
	r = clslst['object']
	scrublowers(r)
	docwrite(r, '', '#')
	docfile.close()
	mdfile.close()


import re
from datetime import timedelta


def get_timedelta(line):
	if line is None:
		return 0
	if line.isdigit():
		line += ' seconds'
	timespaces = {"days": 0}
	for timeunit in "year month week day hour minute second".split():
		content = re.findall(r"([0-9]*?)\s*?" + timeunit, line)
		if content:
			timespaces[timeunit + "s"] = int(content[0])
	timespaces["days"] += 30 * timespaces.pop("months", 0) + 365 * timespaces.pop("years", 0)
	td = timedelta(**timespaces)
	return td.days * 86400 + td.seconds


class Enumerate(object):
	def __init__(self, names):
		for number, name in enumerate(names.split()):
			setattr(self, name, name)


mqttregistered = False
