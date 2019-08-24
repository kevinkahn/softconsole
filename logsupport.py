import json
import sys
import traceback
import multiprocessing
import signal
from queue import Empty as QEmpty
import datetime

import pygame
import webcolors

import fonts
import historybuffer
import hw
import screens.__screens as screens

wc = webcolors.name_to_rgb  # can't use the safe version from utilities due to import loop but this is only used with


# known color names

class TempLogger(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def Log(*args, **kwargs):
		# entry = "".join([unicode(i) for i in args])
		entry = "".join([str(i) for i in args])
		if not isinstance(entry, str): entry = entry.encode('UTF-8', errors='backslashreplace')
		print(time.strftime('%m-%d-%y %H:%M:%S') + " " + entry)



Logs = TempLogger()
import config
import time
import os
import re
from hw import disklogging
from enum import Enum

LogLevels = ('Debug', 'DetailHigh', 'Detail', 'Info', 'Warning', 'Error')
ConsoleDebug = 0
ConsoleDetailHigh = 1
ConsoleDetail = 2
ConsoleInfo = 3
ConsoleWarning = 4
ConsoleError = 5
primaryBroker = None  # for cross system reporting if mqtt is running
errorlogfudge = 0  # force a new log start time for each use of the log to make sure other nodes see it as a change in value due to the alert only on change
LoggerQueue = multiprocessing.Queue()

# Performance info
queuedepthmax = 0
queuetimemax = 0
queuedepthmaxtime = 0
queuetimemaxtime = 0
queuedepthmax24 = 0
queuetimemax24 = 0
queuedepthmax24time = 0
queuetimemax24time = 0
APIXUfetches = 0
APIXUfetches24 = 0
daystartloops = 0
maincyclecnt = 0



Command = Enum('Command', 'LogEntry DevPrint FileWrite CloseHlog StartLog Touch LogRemote LogString DumpRemote')

# logger queue item: (type,str) where type: 0 Logentry, 1 DevPrint, 2 file write (name, access, str), 3 shutdown
# 4 setup logfile 5 touch file  others tbd
AsyncLogger = None

LogLevel = 3
LocalOnly = True


heldstatus = ''


def NewDay(Report=True):
	global queuedepthmax24, queuetimemax24, queuedepthmax24time, queuetimemax24time, APIXUfetches24, daystartloops, maincyclecnt

	if Report:
		Logs.Log("Daily Performance Summary: MaxQDepth: {} at {}".format(queuedepthmax24,
																		 datetime.datetime.fromtimestamp(
																			 queuedepthmax24time).strftime(
																			 "%H:%M:%S.%f")))
		Logs.Log(
			"                           MaxQTime:  {} at {}".format(queuetimemax24, datetime.datetime.fromtimestamp(
				queuetimemax24time).strftime("%H:%M:%S.%f")))
		Logs.Log("                           APIXU Fetches: {}".format(APIXUfetches24))
		Logs.Log("                           Cycles: {}/{}".format(maincyclecnt - daystartloops, maincyclecnt))
	daystartloops = maincyclecnt
	queuedepthmax24 = 0
	queuetimemax24 = 0
	queuedepthmax24time = 0
	queuetimemax24time = 0
	APIXUfetches24 = 0

def SpawnAsyncLogger():
	global AsyncLogger
	AsyncLogger = multiprocessing.Process(name='AsyncLogger', target= LogProcess, args=(LoggerQueue,))
	AsyncLogger.start()
	config.sysStore.SetVal('AsyncLogger_pid', AsyncLogger.pid)

def InitLogs(screen, dirnm):
	global DevPrint
	if config.sysStore.versionname in ('development', 'homerelease'):
		q = [k for k in os.listdir('/home/pi/Console') if 'hlog' in k]
		maxf = config.sysStore.MaxLogFiles
		if "hlog." + str(maxf) in q:
			os.remove('/home/pi/Console/hlog.' + str(maxf))
		for i in range(maxf - 1, 0, -1):
			if "hlog." + str(i) in q:
				os.rename('/home/pi/Console/hlog.' + str(i), "/home/pi/Console/hlog." + str(i + 1))
		try:
			os.rename('/home/pi/Console/hlog','/home/pi/Console/hlog.1')
		except:
			pass
		DevPrint = DevPrintDoIt
	# with open('/home/pi/Console/hlog', 'w') as f:
	#	f.write('------ {} ------\n'.format(time.time()))
	return Logger(screen, dirnm)

def AsyncFileWrite(fn,writestr,access='a'):
	LoggerQueue.put((Command.FileWrite, fn, access, writestr))


historybuffer.AsyncFileWrite = AsyncFileWrite  # to avoid circular imports

def LogProcess(q):
	item = (99, 'init')
	exiting = 0

	def ExitLog(signum, frame):
		nonlocal exiting
		exiting = time.time()
		with open('/home/pi/Console/hlog', 'a') as f:
			f.write('{}({}): Logger process exiting for signal {} exiting: {}\n'.format(os.getpid(),time.time(),signum, exiting))
			f.flush()
		signal.signal(signal.SIGHUP,signal.SIG_IGN)

	def IgnoreHUP(signum, frame):
		with open('/home/pi/Console/hlog', 'a') as f:
			f.write('{}({}): Logger process SIGHUP ignored\n'.format(os.getpid(),time.time()))
			f.flush()



	signal.signal(signal.SIGTERM, ExitLog)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, ExitLog)
	signal.signal(signal.SIGUSR1, ExitLog)
	signal.signal(signal.SIGHUP, IgnoreHUP)
	disklogfile = None
	running = True

	while running:
		try:
			try:
				item = q.get(timeout = 2)
				if exiting !=0:
					with open('/home/pi/Console/hlog', 'a') as f:
						f.write('late item: {} exiting {}\n'.format(item,exiting))
						f.flush()
			except QEmpty:
				if exiting != 0 and time.time() - exiting > 10:
					# exiting got set but we seem stuck - just leave
					with open('/home/pi/Console/hlog', 'a') as f:
						f.write('{}({}): Logger exiting because seems zombied\n'.format(os.getpid(),time.time()))
						f.flush()
					running = False
				elif exiting != 0:  # exiting has been set     todo check if main is alive?
					with open('/home/pi/Console/hlog', 'a') as f:
						f.write('Logger waiting to exit {} {}\n'.format(exiting, time.time()))
						f.flush()
						continue  # nothing to process
				else:
					continue  # back to waiting

			if item[0] == Command.LogEntry:
				# Log Entry (0,severity, entry, entrytime)
				severity, entry, entrytime = item[1:]

				disklogfile.write('{} Sev: {} {}\n'.format(entrytime, severity, entry))
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
			elif item[0] == Command.DevPrint:
				# DevPrint
				with open('/home/pi/Console/hlog', 'a') as f:
					f.write(item[1]+'\n')
					f.flush()
			elif item[0] == Command.FileWrite:
				# general write (2, filename, openaccess, str)
				filename, openaccess, stringitem = item[1:]
				with open(filename, openaccess) as f:
					f.write(stringitem)
					f.flush()
			elif item[0] == Command.CloseHlog:
				# close hlog
				running = False
				with open('/home/pi/Console/hlog', 'a') as f:
					f.write('{}({}): Async Logger ending: {}\n'.format(os.getpid(),time.time(),item[1]))
					f.flush()
				Logs = TempLogger
			elif item[0] == Command.StartLog:
				# open Console log
				os.chdir(item[1])
				disklogfile = open('Console.log', 'w')
				os.chmod('Console.log', 0o555)
			elif item[0] == Command.Touch:
				# liveness touch
				os.utime(item[1],None)
			elif item[0] == Command.LogRemote:
				# remote log (6, node, entry, etime, severity)
				node, entry, etime, severity = item[1:]
				disklogfile.write('{} Sev: {} [{}] {}\n'.format(etime, severity, node, entry))
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
			elif item[0] == Command.LogString:
				# Logentry string (7,entry)
				disklogfile.write('\n'.format(item[1]))
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
			elif item[0] == Command.DumpRemote:  # force remote message dump
				pass
			else:
				with open('/home/pi/Console/hlog', 'a') as f:
					f.write('Log process got garbage: {}\n'.format(item))
					f.flush()
		except Exception as E:
			with open('/home/pi/Console/hlog', 'a') as f:
				f.write('Log process had exception {} handling {}'.format(repr(E), item))
				f.flush()
	try:
		print('{}({}): Logger loop ended'.format(os.getpid(),time.time()))
	except:
		pass
	with open('/home/pi/Console/hlog', 'a') as f:
		f.write('{}({}): Logger loop ended\n'.format(os.getpid(),time.time()))
		f.flush()
	disklogfile.write(
		'{} Sev: {} {}\n'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime(time.time())), 3, "End Log"))
	disklogfile.flush()
	os.fsync(disklogfile.fileno())


def DevPrint(arg):
	pass

def DevPrintDoIt(arg):
	pstr = '{}({}): {}'.format(str(os.getpid()), time.time(), arg)
	LoggerQueue.put((Command.DevPrint, pstr))


def EndAsyncLog():
	LoggerQueue.put((Command.CloseHlog, 0))


historybuffer.DevPrint = DevPrintDoIt  # to avoid circular imports

LogColors = ("teal", "lightgreen", "darkgreen", "white", "yellow", "red")

class Logger(object):
	livelog = True
	livelogpos = 0
	log = []

	def __init__(self, screen, dirnm):
		self.screen = screen
		if disklogging:
			cwd = os.getcwd()
			os.chdir(dirnm)
			q = [k for k in os.listdir('.') if 'Console.log' in k]
			maxf = config.sysStore.MaxLogFiles
			if "Console.log." + str(maxf) in q:
				os.remove('Console.log.' + str(maxf))
			for i in range(maxf - 1, 0, -1):
				if "Console.log." + str(i) in q:
					os.rename('Console.log.' + str(i), "Console.log." + str(i + 1))
			# noinspection PyBroadException
			try:
				os.rename('Console.log', 'Console.log.1')
			except:
				pass
			LoggerQueue.put((Command.StartLog, dirnm))
			#self.disklogfile = open('Console.log', 'w')
			#os.chmod('Console.log', 0o555)
			historybuffer.SetupHistoryBuffers(dirnm, maxf)
			os.chdir(cwd)

	def SetSeverePointer(self, severity):
		if severity in [ConsoleWarning, ConsoleError] and config.sysStore.ErrorNotice == -1:
			config.sysStore.FirstUnseenErrorTime = time.time()
			config.sysStore.ErrorNotice = len(self.log) - 1

	def ReturnRecent(self, loglevel, maxentries):
		if loglevel == -1:
			return self.log
		else:
			rtnval = []
			logitem = len(self.log) - 1
			while len(rtnval) < maxentries and logitem > 0:
				if self.log[logitem][0] >= loglevel:
					rtnval.append(self.log[logitem])
				logitem -= 1
			return rtnval

	def LogRemote(self, node, entry, etime, severity):
		tentry = '[{}] {}'.format(node, entry)
		self.log.append((severity, tentry, time.strftime('%m-%d-%y %H:%M:%S', etime)))
		LoggerQueue.put((Command.LogRemote, node, entry, etime, severity))
		self.SetSeverePointer(severity)

	def RecordMessage(self, severity, entry, entrytime, debugitem, tb):
		if not debugitem:
			self.log.append((severity, entry, entrytime))
			self.SetSeverePointer(severity)
		if disklogging:
			LoggerQueue.put((Command.LogEntry, severity, entry, entrytime))
			if tb:
				DevPrint('Traceback:')
				for line in traceback.format_stack()[0:-2]:
					DevPrint(line.strip())
				frames = traceback.extract_tb(sys.exc_info()[2])
				for f in frames:
					fname, lineno, fn, text = f
					LoggerQueue.put(
						(Command.LogString, '-----------------' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text))


	def Log(self, *args, **kwargs):
		"""
		params: args is one or more strings (like for print) and kwargs is severity=
		"""
		now = time.time()
		localnow = time.localtime(now)
		defentrytime = time.strftime('%m-%d-%y %H:%M:%S', localnow)
		try:
			severity = kwargs.pop('severity', ConsoleInfo)
			entrytime = kwargs.pop('entrytime', time.strftime('%m-%d-%y %H:%M:%S', localnow))
			tb = kwargs.pop('tb', severity == ConsoleError)
			hb = kwargs.pop('hb', False)
			homeonly = kwargs.pop('homeonly', False)
			localonly = kwargs.pop('localonly', False) or LocalOnly  # don't brcst error until mqtt is up
			if homeonly and config.sysStore.versionname not in ('development', 'homerelease'):
				return

			if severity < LogLevel:
				return

			debugitem = kwargs.pop('debugitem', False)
			entry = ''
			for i in args:
				entry = entry + str(i)

			if hb: historybuffer.DumpAll(entry, entrytime)

			self.RecordMessage(severity, entry, entrytime, debugitem, tb)

			# If MQTT is running then broadcast the error
			# suppress reports from development systems
			if severity in [ConsoleWarning, ConsoleError] and not debugitem and config.sysStore.versionname != 'development':
				if primaryBroker is not None and not localonly:
					try:
						primaryBroker.Publish('errors', json.dumps(
							{'node': hw.hostname, 'sev': severity, 'time': entrytime, 'etime': repr(now),
							 'entry': entry}), node='all')
					except Exception as E:
						self.RecordMessage(ConsoleError, "Logger/MQTT error: {}".format(repr(E)),
										   entrytime, debugitem, False)

			# Paint live log to screen during boot
			if self.livelog and not debugitem:
				if self.livelogpos == 0:
					hw.screen.fill(wc('royalblue'))
				self.livelogpos = self.RenderLogLine(entry, LogColors[severity], self.livelogpos)
				if self.livelogpos > hw.screenheight - screens.screenStore.BotBorder:
					time.sleep(1)
					self.livelogpos = 0
				pygame.display.update()

		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while local logging: {}'.format(repr(E)),
							   defentrytime, False, True)


	def RenderLogLine(self, itext, clr, pos):  # todo switch initial log display to using LineRenderer
		# odd logic below is to make sure that if an unbroken item would by itself exceed line length it gets forced out
		# thus avoiding an infinite loop

		text = re.sub('\s\s+', ' ', itext.rstrip())
		ltext = re.split('([ :,])', text)
		ltext.append('')
		ptext = []
		logfont = fonts.fonts.Font(config.sysStore.LogFontSize, face=fonts.monofont)
		while len(ltext) > 1:
			ptext.append(ltext[0])
			del ltext[0]
			while 1:
				if len(ltext) == 0:
					break
				t = logfont.size(''.join(ptext) + ltext[0])[0]
				if t > hw.screenwidth - 10:
					break
				else:
					ptext.append(ltext[0])
					del ltext[0]
			l = logfont.render(''.join(ptext), False, wc(clr))
			self.screen.blit(l, (10, pos))
			ptext = ["    "]
			pos = pos + logfont.get_linesize()
		pygame.display.update()
		return pos

	def PageTitle(self, pageno, itemnumber):
		if len(self.log) > itemnumber:
			return "Local Log from {}           Page: {}".format(self.log[itemnumber][2], pageno), True
		else:
			return "{}Local Log No more entries        Page: {}".format(pageno), False

def ReportStatus(status, retain=True, hold=0):
	# held: 0 normal status report, 1 set an override status to be held, 2 clear and override status
	global heldstatus, queuedepthmax, queuetimemax, queuedepthmaxtime, queuetimemaxtime, queuedepthmax24, queuetimemax24, queuedepthmax24time, queuetimemax24time, APIXUfetches, APIXUfetches24, daystartloops, maincyclecnt
	if hold == 1:
		heldstatus = status
	elif hold == 2:
		heldstatus = ''

	if primaryBroker is not None:
		stat = json.dumps({'status': status if heldstatus == '' else heldstatus, "uptime": time.time() - config.sysStore.ConsoleStartTime,
						   "error": config.sysStore.ErrorNotice, 'rpttime': time.time(),
						   "FirstUnseenErrorTime": config.sysStore.FirstUnseenErrorTime,
						   "GlobalLogViewTime": config.sysStore.GlobalLogViewTime,
						   'queuedepthmax': queuedepthmax, 'queuetimemax': queuetimemax,
						   'queuedepthmaxtime': queuedepthmaxtime,
						   'queuetimemaxtime': queuetimemaxtime, 'queuedepthmax24': queuedepthmax24,
						   'queuetimemax24': queuetimemax24,
						   'queuedepthmax24time': queuedepthmax24time, 'queuetimemax24time': queuetimemax24time,
						   'APIXUfetches': APIXUfetches,
						   'APIXUfetches24': APIXUfetches24, 'daystartloops': daystartloops,
						   'maincyclecnt': maincyclecnt})

		primaryBroker.Publish(node=hw.hostname, topic='status', payload=stat, retain=retain, qos=1,
							  viasvr=True)


def UpdateGlobalErrorPointer(force=False):
	global errorlogfudge
	if primaryBroker is not None:
		if force:
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(1) + '}',
								  node='all')
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(0) + '}',
								  node='all')
		else:
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(
				config.sysStore.LogStartTime + errorlogfudge) + '}', node='all')
			errorlogfudge += 1


def LineRenderer(itemnumber, font, uselog):
	if not (len(uselog) > itemnumber):
		return ' ', False
	itext = uselog[itemnumber][1]
	rl = []
	h = 0
	color = LogColors[uselog[itemnumber][0]]
	text = re.sub('\s\s+', ' ', itext.rstrip())
	ltext = re.split('([ :,])', text)
	ltext.append('')
	ptext = []
	while len(ltext) > 1:
		ptext.append(ltext[0])
		del ltext[0]
		while 1:
			if len(ltext) == 0:
				break
			t = font.size(''.join(ptext) + ltext[0])[0]
			if t > hw.screenwidth - 10:
				break
			else:
				ptext.append(ltext[0])
				del ltext[0]
		rl.append(font.render(''.join(ptext), False, wc(color)))
		h += rl[-1].get_height()
		ptext = ["    "]
	blk = pygame.Surface((hw.screenwidth, h))
	blk.set_colorkey(wc('black'))
	v = 0
	for l in rl:
		blk.blit(l, (0, v))
		v += l.get_height()

	return blk, itemnumber + 1 < len(uselog)
