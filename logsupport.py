import json
import sys
import threading
import traceback
import multiprocessing
import signal
from queue import Empty as QEmpty

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

	def PeriodicRemoteDump(self):
		pass  # dummy to satisfy static method check


Logs = TempLogger()
import config
import time
import os
import re
from hw import disklogging

LogLevels = ('Debug', 'DetailHigh', 'Detail', 'Info', 'Warning', 'Error')
ConsoleDebug = 0
ConsoleDetailHigh = 1
ConsoleDetail = 2
ConsoleInfo = 3
ConsoleWarning = 4
ConsoleError = 5
primaryBroker = None  # for cross system reporting if mqtt is running
LoggerQueue = multiprocessing.Queue()
# logger queue item: (type,str) where type: 0 Logentry, 1 DevPrint, 2 file write (name, access, str), 3 shutdown
# 4 setup logfile others tbd
AsyncLogger = None

LogLevel = 3
LocalOnly = True

heldstatus = ''

def SpawnAsyncLogger():
	global AsyncLogger
	AsyncLogger = multiprocessing.Process(name='AsyncLogger', target= LogProcess, args=(LoggerQueue,))
	AsyncLogger.start()

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
		with open('/home/pi/Console/hlog', 'w') as f:
			f.write('------ {} ------\n'.format(time.time()))
	return Logger(screen, dirnm)

def AsyncFileWrite(fn,writestr,access='a'):
	LoggerQueue.put((2,fn,access,writestr))

def LogProcess(q):
	def ExitLog(signum, frame):
		global exiting
		exiting = time.time()
		print('{}({}): Logger process exiting for signal {} exiting: {}'.format(os.getpid(),time.time(),signum, exiting))
		with open('/home/pi/Console/hlog', 'a') as f:
			f.write('{}({}): Logger process exiting for signal {} exiting: {}'.format(os.getpid(),time.time(),signum, exiting))
			f.flush()
		signal.signal(signal.SIGHUP,signal.SIG_IGN)


	signal.signal(signal.SIGTERM, ExitLog)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, ExitLog)
	signal.signal(signal.SIGUSR1, ExitLog)
	signal.signal(signal.SIGHUP, ExitLog)
	print('Async Logger starting as process {}'.format(os.getpid()))
	disklogfile = None
	running = True
	exiting = 0
	while running:
		try:
			try:
				item = q.get(timeout = 2)
				if exiting !=0:
					print('late item: {} exiting {}'.format(item,exiting))
					with open('/home/pi/Console/hlog', 'a') as f:
						f.write('late item: {} exiting {}'.format(item,exiting))
						f.flush()
			except QEmpty:
				if exiting != 0 and time.time() - exiting > 10:
					# exiting got set but we seem stuck - just leave
					print('{}({}): Logger exiting because seems zombied'.format(os.getpid(),time.time()))
					with open('/home/pi/Console/hlog', 'a') as f:
						f.write('{}({}): Logger exiting because seems zombied'.format(os.getpid(),time.time()))
						f.flush()
					running = False
					#os._exit(0)
				else:
					continue
					#print('{}({}): Logger idle (exiting: {})'.format(os.getpid(),time.time(), exiting))
					#with open('/home/pi/Console/hlog', 'a') as f:
					#	f.write('{}({}): Logger idle (exiting: {})'.format(os.getpid(),time.time(), exiting))
					#	f.flush()
			if item[0] == 0:
				# Log Entry
				disklogfile.write(item[1]+'\n')
				disklogfile.flush()
				os.fsync(disklogfile.fileno())
				pass
			elif item[0] == 1:
				# DevPrint
				with open('/home/pi/Console/hlog', 'a') as f:
					f.write(item[1]+'\n')
					f.flush()
				print(item[1])
			elif item[0] == 2:
				# general write (filename, openaccess, str)
				with open(item[1],item[2]) as f:
					f.write(item[3])
					f.flush()
			elif item[0] == 3:
				running = False
				print('{}({}): Async Logger ending: {}'.format(os.getpid(),time.time(),item[1]))
			elif item[0] == 4:
				#print('{}({}): Open log file in {}'.format(os.getpid(),time.time(),item[1]))
				os.chdir(item[1])
				disklogfile = open('Console.log', 'w')
				os.chmod('Console.log', 0o555)
			else:
				print('Log process got garbage: {}'.format(item))
		except Exception as E:
			print('Log process had exception {} handling {}'.format(repr(E), item))
			with open('/home/pi/Console/hlog', 'a') as f:
				f.write('Log process had exception {} handling {}'.format(repr(E), item))
				f.flush()
	print('{}({}): Logger loop ended'.format(os.getpid(),time.time()))
	with open('/home/pi/Console/hlog', 'a') as f:
		f.write('{}({}): Logger loop ended\n'.format(os.getpid(),time.time()))
		f.flush()


def DevPrint(arg):
	pass

def DevPrintDoIt(arg):
	pstr = '{}({}): {}'.format(str(os.getpid()), time.time(), arg)
	LoggerQueue.put((1, pstr))
	#with open('/home/pi/Console/hlog', 'a') as f:
	#	f.write('{}({}): {}\n'.format(str(os.getpid()), time.time(), arg))
	#print('{}({}): {}'.format(str(os.getpid()), time.time(), arg))


class Logger(object):
	livelog = True
	livelogpos = 0
	log = []

	LogColors = ("teal", "lightgreen", "darkgreen", "white", "yellow", "red")

	def __init__(self, screen, dirnm):
		self.lock = threading.Lock()
		self.lockerid = (0, 'init')
		self.screen = screen
		self.remotenodes = {}
		self.lastremotemes = ''
		self.lastremotesev = ConsoleInfo
		self.lastlocalmes = ''
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
			LoggerQueue.put((4,dirnm))
			#self.disklogfile = open('Console.log', 'w')
			#os.chmod('Console.log', 0o555)
			historybuffer.SetupHistoryBuffers(dirnm, maxf)  # todo ? move print to async
			os.chdir(cwd)

	def SetSeverePointer(self, severity):
		if severity in [ConsoleWarning, ConsoleError] and config.sysStore.ErrorNotice == -1:
			config.sysStore.FirstUnseenErrorTime = time.time()
			config.sysStore.ErrorNotice = len(self.log) - 1

	def LogRemote(self, node, entry, etime, severity):
		locked = False
		try:
			locked = self.lock.acquire(timeout=5)
			if not locked:
				self.RecordMessage(ConsoleError, 'Log lock failed (Remote)' + repr(self.lockerid), '*****Remote******',
								   False, False)
			else:
				self.lockerid = (etime, 'remote')

			if entry == self.lastremotemes:
				if node in self.remotenodes:
					self.remotenodes[node] = (self.remotenodes[node][0], self.remotenodes[node][1] + 1)
				else:
					self.remotenodes[node] = (etime, 1)
			else:
				self.DumpRemoteMes()
				self.lastremotemes = entry
				self.lastremotesev = severity
				self.remotenodes = {node: (etime, 1)}
			if locked:
				self.lock.release()
				self.lockerid = (etime, 'remunlock')
		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while remote logging: {}'.format(repr(E)), '*****Remote******',
							   False, False)
			if locked:
				self.lock.release()
				self.lockerid = (etime, 'remunlockexc')

	def DumpRemoteMes(self):
		now = time.strftime('%m-%d-%y %H:%M:%S')
		if self.lastremotemes == '': return
		ndlist = []
		for nd, info in self.remotenodes.items():
			ndlist.append(nd)
			if info[1] != 1: ndlist[-1] = ndlist[-1] + '(' + str(info[1]) + ')'
		if self.lastremotemes == self.lastlocalmes:
			remoteentry = "Also from: " + ', '.join(ndlist)
		else:
			remoteentry = '[' + ', '.join(ndlist) + ']' + self.lastremotemes
		self.RecordMessage(self.lastremotesev, remoteentry, now, False, False)

		self.lastremotemes = ''

	def RecordMessage(self, severity, entry, entrytime, debugitem, tb):
		if not debugitem:
			self.log.append((severity, entry, entrytime))
			self.SetSeverePointer(severity)
		if disklogging:
			LoggerQueue.put((0,'{} Sev: {} {}'.format(entrytime,severity,entry)))
			#self.disklogfile.write(entrytime + ' Sev: ' + str(severity) + " " + entry + '\n')
			if tb:
				DevPrint('Traceback:')
				for line in traceback.format_stack()[0:-2]:
					DevPrint(line.strip())
				frames = traceback.extract_tb(sys.exc_info()[2])
				for f in frames:
					fname, lineno, fn, text = f
					LoggerQueue.put((0,'-----------------' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text))
					#self.disklogfile.write(
					#	'-----------------' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text + '\n')
			#self.disklogfile.flush()
			#os.fsync(self.disklogfile.fileno())

	def PeriodicRemoteDump(self):
		locked = False
		defentrytime = time.strftime('%m-%d-%y %H:%M:%S')
		try:
			locked = self.lock.acquire(timeout=5)

			if not locked:
				self.RecordMessage(ConsoleError, 'Log lock failed (PeriodicRemote)' + repr(self.lockerid), defentrytime,
								   False, False)
			else:
				self.lockerid = (defentrytime, 'remotedump')
			self.DumpRemoteMes()
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime, 'remotedumpunlk')
		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while dumping periodic remotes: {}'.format(repr(E)),
							   defentrytime, False, False)
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime, 'remotedumpunlkexc')

	def Log(self, *args, **kwargs):
		"""
		params: args is one or more strings (like for print) and kwargs is severity=
		"""
		locked = False
		now = time.time()
		localnow = time.localtime(now)
		defentrytime = time.strftime('%m-%d-%y %H:%M:%S', localnow)
		try:
			locked = self.lock.acquire(timeout=5)

			if not locked:
				self.RecordMessage(ConsoleError, 'Log lock failed (Local)' + repr(self.lockerid) + str(args[0]),
								   defentrytime, False, False)
			else:
				self.lockerid = (defentrytime, 'locallock' + str(args[0]))

			severity = kwargs.pop('severity', ConsoleInfo)
			entrytime = kwargs.pop('entrytime', time.strftime('%m-%d-%y %H:%M:%S', localnow))
			tb = kwargs.pop('tb', severity == ConsoleError)
			hb = kwargs.pop('hb', False)
			homeonly = kwargs.pop('homeonly', False)
			localonly = kwargs.pop('localonly', False) or LocalOnly  # don't brcst error until mqtt is up
			if homeonly and config.sysStore.versionname not in ('development', 'homerelease'):
				if locked:
					self.lock.release()
					self.lockerid = (defentrytime, 'homeonly')
				return

			if severity < LogLevel:
				if locked:
					self.lock.release()
					self.lockerid = (defentrytime, 'loglevelunlk')
				return
			debugitem = kwargs.pop('debugitem', False)
			entry = ''
			for i in args:
				entry = entry + str(i)

			if entry != self.lastremotemes:
				self.DumpRemoteMes()

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
				self.livelogpos = self.RenderLogLine(entry, self.LogColors[severity], self.livelogpos)
				if self.livelogpos > hw.screenheight - screens.botborder:  # todo switch to new screen size stuff
					time.sleep(1)
					self.livelogpos = 0
				pygame.display.update()

			self.lastlocalmes = entry
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime, 'localunlock')

		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while local logging: {}'.format(repr(E)),
							   defentrytime, False, True)
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime, 'localunlockexc')

	def RenderLogLine(self, itext, clr, pos):
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

	def RenderLog(self, backcolor, start=0, pageno=-1):
		pos = 0
		hw.screen.fill(wc(backcolor))
		if pageno != -1:
			pos = self.RenderLogLine(self.log[start][2] + '          Page: ' + str(pageno), 'white', pos)
		for i in range(start, len(self.log)):
			pos = self.RenderLogLine(self.log[i][1], self.LogColors[self.log[i][0]], pos)
			if pos > hw.screenheight - screens.botborder:
				pygame.display.update()
				return (i + 1) if (i + 1) < len(self.log) else -1

		return -1


def ReportStatus(status, retain=True, hold=0):
	# held: 0 normal status report, 1 set an override status to be held, 2 clear and override status
	global heldstatus
	if hold == 1:
		heldstatus = status
	elif hold == 2:
		heldstatus = ''

	if primaryBroker is not None:
		stat = json.dumps({'status': status if heldstatus == '' else heldstatus, "uptime": time.time() - config.sysStore.ConsoleStartTime,
						   "error": config.sysStore.ErrorNotice, 'rpttime': time.time(),
						   "FirstUnseenErrorTime": config.sysStore.FirstUnseenErrorTime,
						   "GlobalLogViewTime": config.sysStore.GlobalLogViewTime})
		primaryBroker.Publish(node=hw.hostname, topic='status', payload=stat, retain=retain, qos=1,
							  viasvr=True)
		Logs.PeriodicRemoteDump()


def UpdateGlobalErrorPointer(force=False):
	if primaryBroker is not None:
		if force:
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(1) + '}',
								  node='all')
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(0) + '}',
								  node='all')
		else:
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(
				config.sysStore.LogStartTime) + '}', node='all')
