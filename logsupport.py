import sys, time, os
import traceback
import multiprocessing
import signal
from queue import Empty as QEmpty
from threading import Lock
import difflib
from datetime import datetime
from setproctitle import setproctitle
import config
from enum import Enum
import re
from utils.hw import disklogging
from utils.utilfuncs import disptime

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
		if not isinstance(entry, str):
			entry = entry.encode('UTF-8', errors='backslashreplace')
		EarlyLog.append((disptime('log'), entry, sev))
		safeprint(" " + entry)

	def write(self, item: str):
		self.Log(item.strip())


Logs = TempLogger()


LogLevels = ('Debug', 'DetailHigh', 'Detail', 'Info', 'Warning', 'Error')
ConsoleDebug = 0
ConsoleDetailHigh = 1
ConsoleDetail = 2
ConsoleInfo = 3
ConsoleWarning = 4
ConsoleError = 5
primaryBroker = None  # for cross system reporting if mqtt is running
errorlogfudge = 0  # force a log start time for each use of log to make sure other nodes see change in value due to
# the alert only on change
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
		if exiting == 0:
			exiting = time.time()
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as fh:
			fh.write(
				'{}({}): Logger process exiting for signal {} exiting: {}\n'.format(os.getpid(), time.time(), signum,
																					exiting))
			fh.flush()
		signal.signal(signal.SIGHUP, signal.SIG_IGN)

	# noinspection PyProtectedMember,PyUnusedLocal
	def ExitAbort(signum, frame):
		with open('/home/pi/.tombstoneL', 'a') as tomb:
			print(f'{disptime()} Logger {os.getpid()} exiting for signal {signum}', file=tomb, flush=True)
			traceback.print_stack(file=tomb)
		os._exit(95)

	# noinspection PyUnusedLocal
	def IgnoreHUP(signum, frame):
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as fhlog:
			fhlog.write('{}({}): Logger process SIGHUP ignored\n'.format(os.getpid(), time.time()))
			fhlog.flush()

	signal.signal(signal.SIGTERM, ExitLog)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, ExitLog)
	signal.signal(signal.SIGUSR1, ExitLog)
	signal.signal(signal.SIGHUP, IgnoreHUP)
	signal.signal(signal.SIGABRT, ExitAbort)
	disklogfile = None
	running = True
	lastmsgtime = 0
	mainpid = 0

	while running:
		try:
			try:
				item = q.get(timeout=2)
				lastmsgtime = time.time()
				if exiting != 0:
					if time.time() - exiting > 5:  # don't note items within few seconds of exit request just process them
						with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
							f.write('@ {} late item: {} exiting {}\n'.format(time.time(), item, exiting))
							f.flush()
			except QEmpty:
				if exiting != 0 and time.time() - exiting > 10:
					# exiting got set but we seem stuck - just leave
					with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
						f.write(f"{os.getpid()}({time.time()}): Logger exiting because seems zombied\n")
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
				except Exception:
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
				os.utime(item[1], None)
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
	except Exception:
		pass
	try:
		with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
			f.write('{}({}): Logger loop ended\n'.format(os.getpid(), time.time()))
			f.flush()
		disklogfile.write(
			'{} Sev: {} {}\n'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime(time.time())), 3, "End Log"))
		disklogfile.flush()
		os.fsync(disklogfile.fileno())
	except Exception as E:
		print(f'----------------- No disk logs to close  {E}')


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
		pass  # time.sleep(1)

	@staticmethod
	def write(buf):
		print(buf)  # also put on stdout
		if len(buf) > 1:
			LoggerQueue.put((Command.LogString,
							 f"{time.strftime('%m-%d-%y %H:%M:%S', time.localtime(time.time()))} -------------Captured Python "
							 f"Exception-------------"))
			for line in buf.rstrip().splitlines():
				LoggerQueue.put((Command.LogString, '       ||          ' + line.rstrip()))
			LoggerQueue.put((Command.LogString,
							 f"{time.strftime('%m-%d-%y %H:%M:%S', time.localtime(time.time()))} ---------------End Captured "
							 f"Exception--------------"))


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
			except Exception:
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

	def SetSeverePointer(self, severity, entry=''):
		if severity in [ConsoleWarning, ConsoleError] and config.sysStore.ErrorNotice == -1:
			config.sysStore.FirstUnseenErrorTime = time.time()
			config.sysStore.ErrorNotice = len(self.log) - 1
			if config.HubLogger is not None:
				config.HubLogger(hw.hostname + 'error indicator set for ' + entry)

	def ReturnRecent(self, loglevel, maxentries):
		if loglevel == -1:
			return self.log[-config.sysStore.MaxLogHistory:]  # todo change to limit size?
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
			rl, localheight = SplitLine(entry, 'black',
										fonts.fonts.Font(config.sysStore.LogFontSize, face=fonts.monofont))
			self.log.append((severity, entry, entrytime, localheight))
			self.SetSeverePointer(severity, entry=entry)
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
							(Command.LogString, '        ->' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text))
					LoggerQueue.put((Command.LogString, '--------------End Traceback--------------'))

	@staticmethod
	def CopyEarly():
		LoggerQueue.put((Command.LogEntry, 3, '-----Copy of PreLog Entries-----', '-----------------'))
		for ent in EarlyLog:
			LoggerQueue.put((Command.LogEntry, ent[2], ent[1], ent[0]))
		LoggerQueue.put((Command.LogEntry, 3, '-----End of PreLog Entries------', '-----------------'))

	def write(self, item: str):
		# used for calling to routines that want to print to log
		self.Log(item.strip())

	# noinspection PyProtectedMember
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
			localonly = kwargs.pop('localonly', False)  # to avoid storms if MQTT is slow don't pub to net from MQTT
			homeonly = kwargs.pop('homeonly', False)
			if homeonly and config.sysStore.versionname not in ('development', 'homerelease'):
				return

			if severity < config.sysStore.LogLevel:
				return

			debugitem = kwargs.pop('debugitem', False)
			entry = ''
			for i in args:
				entry = entry + str(i)

			if hb:
				historybuffer.DumpAll(entry, entrytime)

			self.RecordMessage(severity, entry, entrytime, debugitem, tb)

			# If MQTT is running, past early config errors then broadcast the error
			if severity in [ConsoleWarning, ConsoleError] and not debugitem:
				if primaryBroker is not None and not LocalOnly and not localonly:
					ReportStatus('error rpt')

			# Paint live log to screen during boot
			if self.livelog and not debugitem:
				gotit = self.livelogLock.acquire(timeout=2)
				if not gotit:
					with open('/home/pi/.tombstoneL', 'a') as tomb:
						print(f'{disptime()} Lock aquistion failed for {os.getpid()} Entry: {entry}', file=tomb,
							  flush=True)
						os._exit(97)
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
			for line in tbinfo:  # todo doesn't seem to work?
				print('---{}'.format(line))
				self.RecordMessage(ConsoleError, '{}'.format(line), defentrytime, False, True)

	# noinspection DuplicatedCode
	def RenderLogLine(self, itext, clr, pos):  # todo switch initial log display to using LineRenderer
		# odd logic below is to make sure that if an unbroken item would by itself exceed line length it gets forced out
		# thus avoiding an infinite loop
		logfont = fonts.fonts.Font(config.sysStore.LogFontSize, face=fonts.monofont)

		lines, h = SplitLine(itext, clr, logfont)
		while self.screen.get_locked():
			print("Locked {}".format(self.screen.get_locks()))
		for line in lines:
			self.screen.blit(line, (10, pos))
			pos = pos + logfont.get_linesize()
		displayupdate.updatedisplay()
		return pos

	def PageTitle(self, pageno, itemnumber):
		if len(self.log) > itemnumber:
			return f"Local Log from {self.log[itemnumber][2]}           Page: {pageno}       {time.strftime('%c')}", True
		else:
			return f"Local Log No more entries        Page: {pageno}      {time.strftime('%c')}", False


def LineRenderer(itemnumber, logfont, uselog, RenderHeight=0):
	if RenderHeight > 0 and len(uselog[itemnumber]) > 3:
		usedheight = 0
		while itemnumber < len(uselog):
			usedheight += uselog[itemnumber][3]
			itemnumber += 1
			if usedheight > RenderHeight:
				break
		return itemnumber, itemnumber + 1 < len(uselog), usedheight
	if not (len(uselog) > itemnumber):
		return None, False, 0
	itext = uselog[itemnumber][1]
	rl, h = SplitLine(itext, LogColors[uselog[itemnumber][0]], logfont)

	blk = pg.Surface((hw.screenwidth, h))
	blk.set_colorkey(wc('black'))
	v = 0
	for line in rl:
		blk.blit(line, (0, v))
		v += line.get_height()

	return blk, itemnumber + 1 < len(uselog), v


def SplitLine(itext, color, logfont):
	# takes a text line and returns rendered multiline if needed block and total height
	rl = []
	totalheight = 0
	text = re.sub('\s\s+', ' ', itext.rstrip())
	ltext = re.split('([ :,])', text)
	ltext.append('')
	ptext = []
	while len(ltext) > 1:
		# noinspection DuplicatedCode
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
		totalheight += rl[-1].get_height()
		ptext = ["    "]

	return rl, totalheight
