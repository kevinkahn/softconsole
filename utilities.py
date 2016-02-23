import collections
import os
import sys
import time
from sets import Set

import pygame

import config
import fonts
import hw
from logsupport import Error

globdoc = {}
moddoc = {}
paramlog = []
exemplarobjs = collections.OrderedDict()


class clsstruct:
	def __init__(self, nm):
		self.name = nm
		self.members = []
		self.membernms = Set()

	def addmem(self, nm):
		self.membernms.add(nm)


clslst = {}
doclst = {}


def register_example(str, obj):
	exemplarobjs[str] = list(dir(obj))
	mro = list(obj.__class__.__mro__)
	mro.reverse()
	for i in range(len(mro)):
		t = mro[i]
		if t.__name__ not in clslst:
			doclst[t.__name__] = t.__doc__
			clslst[t.__name__] = clsstruct(t.__name__)
		for e in mro[i + 1:]:
			clslst[t.__name__].addmem(e.__name__)


def interval_str(sec_elapsed):
	d = int(sec_elapsed/(60*60*24))
	h = int((sec_elapsed%(60*60*24))/3600)
	m = int((sec_elapsed%(60*60))/60)
	s = int(sec_elapsed%60)
	return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)


def scaleW(p):
	return int(round(float(p)*float(config.dispratioW)))


def scaleH(p):
	return int(round(float(p)*float(config.dispratioH)))


def ParseParam(param):
	global paramlog
	for p in param.__dict__:
		if '__' not in p:
			p2 = p.replace('_', '', 1) if p.startswith('_') else p
			config.__dict__[p2] = type(param.__dict__[p])(config.ParsedConfigFile.get(p2, param.__dict__[p]))
			globdoc[p2] = (type(param.__dict__[p]), param.__dict__[p])
			if not p.startswith('_'):
				# can't log directly because logger isn't initialized yet at the point this is called
				paramlog.append('Param: ' + p + ": " + str(config.__dict__[p2]))


def LogParams():
	global paramlog
	for p in paramlog:
		config.Logs.Log(p)


def signal_handler(sig, frame):
	print "Signal: {}".format(sig)
	print "pid: ", os.getpid()
	time.sleep(1)
	pygame.quit()
	print time.time(), "Console Exiting"
	sys.exit(0)


def daemon_died(sig, frame):
	print "CSignal: {}".format(sig)
	if config.DaemonProcess is None:
		return
	if config.DaemonProcess.is_alive():
		print "Child ok"
	else:
		print time.time(), "Daemon died!"
		pygame.quit()
		sys.exit()


def InitializeEnvironment():
	"""
	os.environ['SDL_FBDEV'] = '/dev/fb1'
	os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
	os.environ['SDL_MOUSEDRV'] = 'TSLIB'
	os.environ['SDL_VIDEODRIVER'] = 'fbcon'
	"""
	hw.initOS()
	pygame.display.init()
	config.fonts = fonts.Fonts()
	config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)

	#    config.screenwidth = 240  # todo 2 lines for test only
	#    config.screenheight = 320

	"""
	Scale screen constants
	"""
	config.dispratioW = float(config.screenwidth)/float(config.basewidth)
	config.dispratioH = float(config.screenheight)/float(config.baseheight)
	config.horizborder = scaleW(config.horizborder)
	config.topborder = scaleH(config.topborder)
	config.botborder = scaleH(config.botborder)
	config.cmdvertspace = scaleH(config.cmdvertspace)

	config.screen = pygame.display.set_mode((config.screenwidth, config.screenheight), pygame.FULLSCREEN)
	config.screen.fill((0, 0, 0))  # clear screen
	pygame.display.update()
	if hw.touchdevice:
		pygame.mouse.set_visible(False)  # no cursor
	pygame.fastevent.init()


def LocalizeParams(inst, configsection, *args, **kwargs):
	"""
	Merge screen specific parameter values into self.<var> entries for the class
	inst is the class object (self), configsection is the Section of the config.txt file for this object,
		args are any global parameters (see globalparams.py) for which local overrides make sense and are used
	after the call there will be self.xxx variables for all relevant paramters
	kwargs are locally defined parameters for this object and a default value which also gets added as self.xxx and
		a value is taken from the config section if present
	:param inst:
	:param screensection:
	:param args:
	:param kwargs:
	:return:
	"""
	global moddoc
	if not inst.__class__.__name__ in moddoc:
		moddoc[inst.__class__.__name__] = {'loc': {}, 'ovrd': set()}
	if configsection is None:
		configsection = {}
	lcllist = []
	lclval = []
	for nametoadd in kwargs:
		if nametoadd not in inst.__dict__:
			lcllist.append(nametoadd)
			lclval.append(kwargs[nametoadd])
			moddoc[inst.__class__.__name__]['loc'][lcllist[-1]] = type(lclval[-1])
		else:
			print 'why dup', nametoadd
	for nametoadd in args:
		if nametoadd in config.__dict__:
			lcllist.append(nametoadd)
			lclval.append(config.__dict__[nametoadd])
			moddoc[inst.__class__.__name__]['ovrd'].add(lcllist[-1])
		else:
			config.Logs.Log("Obj " + inst.__class__.__name__ + ' attempted import of non-existent global ' + nametoadd,
							severity=Error)
	for i in range(len(lcllist)):
		inst.__dict__[lcllist[i]] = type(lclval[i])(configsection.get(lcllist[i], lclval[i]))


def DumpDocumentation():
	docfile = open('docs/params.txt', 'w')
	os.chmod('docs/params.txt', 0o555)
	# todo make this a command line option since only need to do for development purposes
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
	mdfile.write('\# Class/Attribute Structure):\n')
	mdfile.write('\n')

	varsinuse = {}
	olditems = []
	for i, scr in exemplarobjs.iteritems():
		varsinuse[i] = [x for x in scr if not x.startswith('_') and x not in olditems]
		olditems = olditems + [x for x in scr if not x.startswith('_')]

	def scrublowers(r):
		lower = []
		rtn = list(r.members)
		for i in r.members:
			lower = lower + scrublowers(i)
		r.members = [x for x in r.members if x not in lower]
		return rtn

	def docwrite(r, ind, md):
		docfile.write(ind + r.name + ': [' + ', '.join([n.name for n in r.members]) + ']\n')
		mdfile.write(md + r.name + ': [' + ', '.join([n.name for n in r.members]) + ']\n')
		docfile.write(ind + (doclst[r.name] if not doclst[r.name] is None else "***missing***") + '\n')
		mdfile.write((doclst[r.name] if not doclst[r.name] is None else "***missing***") + '\n')
		if r.name in varsinuse:
			for v in varsinuse[r.name]:
				docfile.write(ind + '  ' + v + '\n')
				mdfile.write('*  ' + v + '\n')
		for i in r.members:
			docwrite(i, ind + '    ', '##')

	for c in clslst.itervalues():
		for n in c.membernms:
			c.members.append(clslst[n])
	r = clslst['object']
	scrublowers(r)
	docwrite(r, '', '#')
	docfile.close()
	mdfile.close()
