import sys
import traceback
import multiprocessing
import signal
from queue import Empty as QEmpty
from threading import Lock
import difflib
from datetime import datetime
from setproctitle import setproctitle

from guicore.screencallmanager import pg

import webcolors

from typing import Callable, Union
from utils import fonts, displayupdate, hw
import historybuffer
import screens.__screens as screens
from utils.utilfuncs import safeprint

wc = webcolors.name_to_rgb  # can't use the safe version from utilities due to import loop but this is only used with

# known color names

ReportStatus: Union[Callable, None] = None
EarlyLog = []


class TempLogger(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def Log(*args, **kwargs):
		global EarlyLog
		# entry = "".join([unicode(i) for i in args])
		entry = "".join([str(i) for i in args])
		sev = 3 if 'severity' not in kwargs else kwargs['severity']
		if not isinstance(entry, str): entry = entry.encode('UTF-8', errors='backslashreplace')
		EarlyLog.append((time.strftime('%m-%d-%y %H:%M:%S'), entry, sev))
		safeprint(" " + entry)



Logs = TempLogger()
import config
import time
import os
import re
from utils.hw import disklogging
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

# noinspection PyArgumentList
Command = Enum('Command', 'LogEntry DevPrint FileWrite CloseHlog StartLog Touch LogString DumpRemote')

# logger queue item: (type,str) where type: 0 Logentry, 1 DevPrint, 2 file write (name, access, str), 3 shutdown
# 4 setup logfile 5 touch file  others tbd
AsyncLogger = None

# config.sysStore.LogLevel = 3
LocalOnly = True



def SpawnAsyncLogger():
	global AsyncLogger
	AsyncLogger = multiprocessing.Process(name='AsyncLogger', target=LogProcess, args=(LoggerQueue,))
	AsyncLogger.start()
	config.sysStore.SetVal('AsyncLogger_pid', AsyncLogger.pid)


def InitLogs(screen, dirnm):
	return Logger(screen, dirnm)


def AsyncFileWrite(fn, writestr, access='a'):
	LoggerQueue.put((Command.FileWrite, fn, access, writestr))


historybuffer.AsyncFileWrite = AsyncFileWrite  # to avoid circular imports


# noinspection PyBroadException
def LogProcess(q):
	global Logs
	setproctitle('Console Logger')
	item = (99, 'init')
	exiting = 0

	# noinspection PyUnusedLocal
	def ExitLog(signum, frame):
		nonlocal exiting
		exiting = time.time()
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as fh:
			fh.write(
				'{}({}): Logger process exiting for signal {} exiting: {}\n'.format(os.getpid(), time.time(), signum,
																					exiting))
			fh.flush()
		signal.signal(signal.SIGHUP, signal.SIG_IGN)

	# noinspection PyUnusedLocal
	def IgnoreHUP(signum, frame):
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as fhlog:
			fhlog.write('{}({}): Logger process SIGHUP ignored\n'.format(os.getpid(), time.time()))
			fhlog.flush()

	signal.signal(signal.SIGTERM, ExitLog)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, ExitLog)
	signal.signal(signal.SIGUSR1, ExitLog)
	signal.signal(signal.SIGHUP, IgnoreHUP)
	disklogfile = None
	running = True
	lastmsgtime = 0
	mainpid = 0

	while running:
		try:
			try:
				item = q.get(timeout = 2)
				lastmsgtime = time.time()
				if exiting !=0:
					if time.time() - exiting > 3:  # don't note items within few seconds of exit request just process them
						with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
							f.write('@ {} late item: {} exiting {}\n'.format(time.time(), item, exiting))
							f.flush()
			except QEmpty:
				if exiting != 0 and time.time() - exiting > 10:
					# exiting got set but we seem stuck - just leave
					with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
						f.write('{}({}): Logger exiting because seems zombied\n'.format(os.getpid(),time.time()))
						f.flush()
					running = False
					continue
				elif exiting != 0:  # exiting has been set     todo check if main is alive?
					with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
						f.write('Logger waiting to exit {} {}\n'.format(exiting, time.time()))
						f.flush()
					continue  # nothing to process
				else:
					if time.time() - lastmsgtime > 3600:
						with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
							f.write('Logger extended quiet at {} lastmsg {}\n'.format(time.time(), lastmsgtime))
							f.flush()
							lastmsgtime = time.time()  # reset for quiet message
						try:
							os.kill(mainpid, 0)
							# running
							with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
								f.write('Main {} still running\n'.format(mainpid))
								f.flush()
						except OSError:
							# not running
							with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
								f.write('Main {} seems dead - exiting\n'.format(mainpid))
								f.flush()
								running = False
					continue  # back to waiting

			if item[0] == Command.LogEntry:
				# Log Entry (0,severity, entry, entrytime)
				severity, entry, entrytime = item[1:]

				disklogfile.write('{} Sev: {} {}\n'.format(entrytime, severity, entry))
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
			elif item[0] == Command.DevPrint:
				# DevPrint
				with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
					f.write(item[1]+'\n')
					f.flush()
			elif item[0] == Command.FileWrite:
				# general write (2, filename, openaccess, str)
				filename, openaccess, stringitem = item[1:]
				with open(filename, openaccess) as f:
					f.write(stringitem)
					f.flush()
			elif item[0] == Command.CloseHlog:
				running = False
				try:
					with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
						f.write('{}({}): Async Logger ending: {}\n'.format(os.getpid(), time.time(), item[1]))
						f.flush()
				except:
					pass  # hlog was never set up
				Logs = TempLogger
			elif item[0] == Command.StartLog:
				# open Console log
				os.chdir(item[1])
				mainpid = item[2]
				disklogfile = open('Console.log', 'w')
				os.chmod('Console.log', 0o555)
				with open('/home/pi/Console/.HistoryBuffer/hlog', 'w') as f:
					f.write('Starting hlog for {} at {} main pid: {}\n'.format(os.getpid(), time.time(), mainpid))
					f.flush()
			elif item[0] == Command.Touch:
				# liveness touch
				os.utime(item[1],None)
			elif item[0] == Command.LogString:
				# Logentry string (7,entry)
				disklogfile.write('{}\n'.format(item[1]))
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
			elif item[0] == Command.DumpRemote:  # force remote message dump
				pass
			else:
				with open('/home/pi/Console/hlogerror', 'a') as f:
					f.write(
						'{} Log process got garbage: {}\n'.format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), item))
					f.flush()
		except Exception as E:
			with open('/home/pi/Console/hlogerror', 'a') as f:
				f.write(
					'{} Log process had exception {} handling {}'.format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
																		 repr(E), item))
				f.flush()
	try:
		print('----------------- {}({}): Logger loop ended'.format(os.getpid(), time.time()))
	except:
		pass
	try:
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
			f.write('{}({}): Logger loop ended\n'.format(os.getpid(), time.time()))
			f.flush()
		disklogfile.write(
			'{} Sev: {} {}\n'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime(time.time())), 3, "End Log"))
		disklogfile.flush()
		os.fsync(disklogfile.fileno())
	except:
		print('----------------- No disk logs to close')


def DevPrintInit(arg):
	pstr = '{}({}): {}'.format(str(os.getpid()), time.time(), arg)
	print(pstr)

def DevPrintDoIt(arg):
	pstr = '{}({}): {}'.format(str(os.getpid()), time.time(), arg)
	LoggerQueue.put((Command.DevPrint, pstr))


DevPrint = DevPrintInit


def EndAsyncLog():
	LoggerQueue.put((Command.CloseHlog, 0))


historybuffer.DevPrint = DevPrintDoIt  # to avoid circular imports

LogColors = ("teal", "lightgreen", "darkgreen", "white", "yellow", "red")


class Stream_to_Logger(object):
	def __init__(self):
		pass

	@staticmethod
	def flush():
		time.sleep(1)

	@staticmethod
	def write(buf):
		print(buf)  # also put on stdout
		if len(buf) > 1:
			LoggerQueue.put((Command.LogString, '-------------Captured Python Exception-------------'))
			for line in buf.rstrip().splitlines():
				LoggerQueue.put((Command.LogString, line.rstrip()))
			LoggerQueue.put((Command.LogString, '---------------End Captured Exception--------------'))


class Logger(object):
	log = []

	def __init__(self, screen, dirnm):
		global DevPrint
		self.screen = screen
		self.livelog = True
		self.livelogLock = Lock()
		self.livelogpos = 0
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
			LoggerQueue.put((Command.StartLog, dirnm, os.getpid()))
			# self.disklogfile = open('Console.log', 'w')
			# os.chmod('Console.log', 0o555)
			historybuffer.SetupHistoryBuffers(dirnm, maxf)
			with open('/home/pi/Console/.HistoryBuffer/hlog', 'w') as f:
				f.write('------ {} pid: {} ------\n'.format(time.time(), os.getpid()))
			DevPrint = DevPrintDoIt
			sys.stderr = Stream_to_Logger()
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

	def MatchLastErr(self, lev, msg, reptlev):
		firstunseen = config.sysStore.ErrorNotice
		for i in range(len(self.log) - 1, firstunseen - 1, -1):
			if self.log[i][0] == lev and difflib.SequenceMatcher(None, self.log[i][1], msg).ratio() > .9:
				return True
			elif self.log[i][0] >= reptlev:
				# equal or worse error after match target
				return False
		return False  # didn't match

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
				DevPrint('End Traceback')
				frames = traceback.extract_stack()  # traceback.extract_tb(sys.exc_info()[2])
				if len(frames) > 0:
					LoggerQueue.put((Command.LogString, '-------------Start Traceback-------------'))
					for f in frames[:-2]:
						fname, lineno, fn, text = f
						LoggerQueue.put(
							(Command.LogString, '->' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text))
					LoggerQueue.put((Command.LogString, '--------------End Traceback--------------'))

	@staticmethod
	def CopyEarly():
		LoggerQueue.put((Command.LogEntry, 3, '-----Copy of PreLog Entries-----', '-----------------'))
		for ent in EarlyLog:
			LoggerQueue.put((Command.LogEntry, ent[2], ent[1], ent[0]))
		LoggerQueue.put((Command.LogEntry, 3, '-----End of PreLog Entries------', '-----------------'))

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
			localonly = kwargs.pop('localonly',
								   False)  # to avoid error storms if MQTT is slow don't pub to net from MQTT
			homeonly = kwargs.pop('homeonly', False)
			if homeonly and config.sysStore.versionname not in ('development', 'homerelease'):
				return

			if severity < config.sysStore.LogLevel:
				return

			debugitem = kwargs.pop('debugitem', False)
			entry = ''
			for i in args:
				entry = entry + str(i)

			if hb: historybuffer.DumpAll(entry, entrytime)

			self.RecordMessage(severity, entry, entrytime, debugitem, tb)

			# If MQTT is running, past early config errors then broadcast the error
			if severity in [ConsoleWarning, ConsoleError] and not debugitem:
				if primaryBroker is not None and not LocalOnly and not localonly:
					ReportStatus('error rpt')

			# Paint live log to screen during boot
			if self.livelog and not debugitem:
				self.livelogLock.acquire()
				if self.livelogpos == 0:
					hw.screen.fill(wc('royalblue'))
				self.livelogpos = self.RenderLogLine(entry, LogColors[severity], self.livelogpos)
				if self.livelogpos > hw.screenheight - screens.screenStore.BotBorder:
					time.sleep(1)
					self.livelogpos = 0
				displayupdate.updatedisplay()
				self.livelogLock.release()

		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while local logging: {}'.format(repr(E)),
							   defentrytime, False, True)
			tbinfo = traceback.format_exc().splitlines()
			for l in tbinfo:  # todo doesn't seem to work?
				print('---{}'.format(l))
				self.RecordMessage(ConsoleError, '{}'.format(l),
								   defentrytime, False, True)


	def RenderLogLine(self, itext, clr, pos):  # todo switch initial log display to using LineRenderer
		# odd logic below is to make sure that if an unbroken item would by itself exceed line length it gets forced out
		# thus avoiding an infinite loop

		text = re.sub('\s\s+', ' ', itext.rstrip())
		ltext = re.split('([ :,])', text)
		ltext.append('')
		logfont = fonts.fonts.Font(config.sysStore.LogFontSize, face=fonts.monofont)

		ptext = []
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
			while self.screen.get_locked():
				print("Locked {}".format(self.screen.get_locks()))
			self.screen.blit(l, (10, pos))
			ptext = ["    "]
			pos = pos + logfont.get_linesize()
		displayupdate.updatedisplay()
		return pos

	def PageTitle(self, pageno, itemnumber):
		if len(self.log) > itemnumber:
			return "Local Log from {}           Page: {}       {}".format(self.log[itemnumber][2], pageno,
																		  time.strftime('%c')), True
		else:
			return "Local Log No more entries        Page: {}      {}".format(pageno, time.strftime('%c')), False


def LineRenderer(itemnumber, logfont, uselog):
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
			t = logfont.size(''.join(ptext) + ltext[0])[0]
			if t > hw.screenwidth - 10:
				break
			else:
				ptext.append(ltext[0])
				del ltext[0]
		rl.append(logfont.render(''.join(ptext), False, wc(color)))
		h += rl[-1].get_height()
		ptext = ["    "]
	blk = pg.Surface((hw.screenwidth, h))
	blk.set_colorkey(wc('black'))
	v = 0
	for l in rl:
		blk.blit(l, (0, v))
		v += l.get_height()

	return blk, itemnumber + 1 < len(uselog)
