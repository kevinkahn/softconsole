import collections
import os
import signal
import time
import socket
import threadmanager  # should not depend on in project files - move somewhere else
import json
# from sets import Set

import pygame

import config
import fonts
import hw
import logsupport
from logsupport import ConsoleDetail
import debug

globdoc = {}
moddoc = {}
paramlog = []
exemplarobjs = collections.OrderedDict()

# next several lines stolen from https://stackoverflow.com/questions/39198961/pygame-init-fails-when-run-with-systemd
# this handles some weird random SIGHUP when initializing pygame, it's really a hack to work around it
# Not really sure what other ill effects this might have!!!
def handler(signum, frame):
	print('Systemd signal hack raised', signum, repr(frame))
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


def scaleW(p):
	return int(round(float(p)*float(config.dispratioW)))


def scaleH(p):
	return int(round(float(p)*float(config.dispratioH)))

def LogParams():
	global paramlog
	for p in paramlog:
		logsupport.Logs.Log(p,severity=ConsoleDetail)

def InitializeEnvironment():
	# this section is an unbelievable nasty hack - for some reason Pygame
	# needs a keyboardinterrupt to initialise in some limited circs (second time running)
	# lines below commented with HACK also part of workaround
	# see https://stackoverflow.com/questions/17035699/pygame-requires-keyboard-interrupt-to-init-display
	class Alarm(Exception):
		pass

	def alarm_handler(signum, frame):
		print('Hack alarm raised',signum,repr(frame))
		raise Alarm

	# end hack
	try:
		with open(config.homedir + "/.Screentype") as f:
			config.screentype = f.readline().rstrip('\n')
	except IOError:
		config.screentype = "*Unknown*"

	hw.initOS(config.screentype)
	pygame.display.init()
	config.hostname = socket.gethostname()
	config.starttime = time.time()
	config.fonts = fonts.Fonts()
	config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)

	config.personalsystem = os.path.isfile(config.homedir + "/homesystem")

	if config.screentype in ('pi7','35r','28c'):
		from touchhandler import Touchscreen, TS_PRESS, TS_RELEASE, TS_MOVE
		ts = Touchscreen()
		def touchhandler(event,touch):
			p = (touch.x,touch.y)
			if event == TS_PRESS:
				e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': p})
				debug.debugPrint('Touch','Press: '+str(p))
				pygame.fastevent.post(e)
			elif event == TS_RELEASE:
				e = pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': p})
				debug.debugPrint('Touch', 'Release: ' + str(p))
				pygame.fastevent.post(e)
			elif event == TS_MOVE:
				e = pygame.event.Event(pygame.MOUSEMOTION, {'pos': p})
				debug.debugPrint('Touch', 'Motion: ' + str(p))
				pygame.fastevent.post(e)


		for touchtyp in ts.touches:
			touchtyp.on_press = touchhandler
			touchtyp.on_release = touchhandler
			touchtyp.on_move = touchhandler

		threadmanager.SetUpHelperThread('TouchHandler',ts.run)

	if config.screenwidth > config.screenheight:
		config.portrait = False
	try:
		config.lastup = os.path.getmtime(config.homedir + "/.ConsoleStart")
		with open(config.homedir + "/.ConsoleStart") as f:
			laststart = float(f.readline())
			lastrealstart = float(f.readline())
		config.previousup = config.lastup - lastrealstart
		prevsetup = lastrealstart - laststart
	except (IOError, ValueError):
		config.previousup = -1
		config.lastup = -1
		prevsetup = -1

	with open(config.homedir + "/.RelLog", "a") as f:
		f.write(
			str(config.starttime) + ' ' + str(prevsetup) + ' ' + str(config.previousup) + ' ' + str(config.lastup) + ' '
			+ str(config.starttime - config.lastup) + '\n')

	"""
	Scale screen constants
	"""
	config.dispratioW = float(config.screenwidth)/float(config.basewidth)
	config.dispratioH = float(config.screenheight)/float(config.baseheight)
	config.horizborder = scaleW(config.horizborder)
	config.topborder = scaleH(config.topborder)
	config.botborder = scaleH(config.botborder)
	config.cmdvertspace = scaleH(config.cmdvertspace)
	signal.signal(signal.SIGALRM, alarm_handler)  # HACK
	signal.alarm(3)  # HACK
	try:  # HACK
		config.screen = pygame.display.set_mode((config.screenwidth, config.screenheight),
												pygame.FULLSCREEN)  # real needed line
		signal.alarm(0)  # HACK
	except Alarm:  # HACK
		raise KeyboardInterrupt  # HACK

	config.screen.fill((0, 0, 0))  # clear screen
	pygame.display.update()
	if hw.touchdevice:
		pygame.mouse.set_visible(False)  # no cursor
	pygame.fastevent.init()



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
	timespaces["days"] += 30*timespaces.pop("months", 0) + 365*timespaces.pop("years", 0)
	td = timedelta(**timespaces)
	return td.days*86400 + td.seconds


class Enumerate(object):
	def __init__(self, names):
		for number, name in enumerate(names.split()):
			setattr(self, name, name)


def ReportStatus(status):
	# todo: status should have lasterror, thread numbers for subhandlers, uptime, etc. as a json record
	if config.primaryBroker is not None:
		stat = json.dumps({'status': status, "uptime": time.time() - config.starttime,
						   "error": config.sysStore.ErrorNotice})
		config.primaryBroker.MQTTclient.publish('consoles/' + config.hostname + '/status', stat, retain=True, qos=1)


def RegisterConsole():
	if config.primaryBroker is not None:
		config.primaryBroker.MQTTclient.publish('consoles/all/nodes/' + config.hostname,
												json.dumps(
													{'registered': time.time(), 'versionname': config.versionname,
													 'versionsha': config.versionsha, 'versiondnld': config.versiondnld,
													 'versioncommit': config.versioncommit,
													 'boottime': config.bootime, 'osversion': config.osversion,
													 'hw': config.hwinfo}),
												retain=True, qos=1)
