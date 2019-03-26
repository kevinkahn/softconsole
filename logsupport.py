import fonts
import historybuffer
import pygame
import webcolors
import sys
import traceback
import json
import threading

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
		#entry = "".join([unicode(i) for i in args])
		entry = "".join([str(i) for i in args])
		if not isinstance(entry, str): entry =  entry.encode('UTF-8', errors='backslashreplace')
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

LogLevel = 3
LocalOnly = True

# try:
#	return isinstance(obj, basestring)
# except NameError:
#	return isinstance(obj, str)


def InitLogs(screen,dirnm):
	return Logger(screen,dirnm)


class Logger(object):
	livelog = True
	livelogpos = 0
	log = []

	LogColors = ("teal", "lightgreen", "darkgreen", "white", "yellow", "red")

	def __init__(self, screen, dirnm):
		self.lock = threading.Lock()
		self.lockerid = (0,'init')
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
			self.disklogfile = open('Console.log', 'w')
			os.chmod('Console.log', 0o555)
			historybuffer.SetupHistoryBuffers(dirnm, maxf)
			os.chdir(cwd)

	def SetSeverePointer(self, severity):
		if severity in [ConsoleWarning, ConsoleError] and config.sysStore.ErrorNotice == -1:
			config.sysStore.FirstUnseenErrorTime = time.time()
			config.sysStore.ErrorNotice = len(self.log) - 1

	def LogRemote(self, node, entry, etime, severity):
		locked = False
		try:
			locked = self.lock.acquire(timeout=1)
			if not locked:
				self.RecordMessage(ConsoleError, 'Log lock failed (Remote)'+repr(self.lockerid), '*****Remote******', False, False)
			else:
				self.lockerid = (etime,'remote')

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
				self.lockerid = (etime,'remunlock')
		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while remote logging: {}'.format(repr(E)), '*****Remote******',
							   False, False)
			if locked:
				self.lock.release()
				self.lockerid = (etime,'remunlockexc')

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
			self.disklogfile.write(entrytime + ' Sev: ' + str(severity) + " " + entry + '\n')
			if severity == ConsoleError and tb:
				# traceback.print_stack(file=self.disklogfile)
				for line in traceback.format_stack():
					print(line.strip())
				frames = traceback.extract_tb(sys.exc_info()[2])
				for f in frames:
					fname, lineno, fn, text = f
					self.disklogfile.write(
						'-----------------' + fname + ':' + str(lineno) + ' ' + fn + ' ' + text + '\n')
			self.disklogfile.flush()
			os.fsync(self.disklogfile.fileno())

	def PeriodicRemoteDump(self):
		locked = False
		defentrytime = time.strftime('%m-%d-%y %H:%M:%S')
		try:
			locked = self.lock.acquire(timeout=3)

			if not locked:
				self.RecordMessage(ConsoleError, 'Log lock failed (PeriodicRemote)'+repr(self.lockerid), defentrytime, False, False)
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
				self.RecordMessage(ConsoleError, 'Log lock failed (Local)'+repr(self.lockerid), defentrytime, False, False)
			else:
				self.lockerid = (defentrytime,'locallock')

			severity = kwargs.pop('severity', ConsoleInfo)
			entrytime = kwargs.pop('entrytime', time.strftime('%m-%d-%y %H:%M:%S', localnow))
			tb = kwargs.pop('tb', True)
			hb = kwargs.pop('hb', False)
			localonly = kwargs.pop('localonly', False) or LocalOnly  # don't brcst error unti mqtt is up

			if severity < LogLevel:
				if locked: self.lock.release()
				return
			debugitem = kwargs.pop('debugitem', False)
			entry = ''
			for i in args:
				entry = entry + str(i)
			# if isinstance(i, str): todo del
			#	if not isinstance(i, str):
			#		entry = entry + i.encode('UTF-8', errors='backslashreplace')
			#	else:
			#		entry = entry + i
			# else:
			#	entry = entry + str(i)

			if entry != self.lastremotemes:
				self.DumpRemoteMes()

			if hb: historybuffer.DumpAll(entry, entrytime)

			self.RecordMessage(severity, entry, entrytime, debugitem, tb)

			# If MQTT is running then broadcast the error
			# suppress reports from development systems
			if severity in [ConsoleWarning, ConsoleError] and not debugitem and config.versionname != 'development':
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
					config.screen.fill(wc('royalblue'))
				self.livelogpos = self.RenderLogLine(entry, self.LogColors[severity], self.livelogpos)
				if self.livelogpos > hw.screenheight - screens.botborder: # todo switch to new screen size stuff
					time.sleep(1)
					self.livelogpos = 0
				pygame.display.update()

			self.lastlocalmes = entry
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime,'localunlock')
		except Exception as E:
			self.RecordMessage(ConsoleError, 'Exception while local logging: {}'.format(repr(E)),
							   defentrytime, False, False)
			if locked:
				self.lock.release()
				self.lockerid = (defentrytime,'localunlockexc')

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
		config.screen.fill(wc(backcolor))
		if pageno != -1:
			pos = self.RenderLogLine(self.log[start][2] + '          Page: ' + str(pageno), 'white', pos)
		for i in range(start, len(self.log)):
			pos = self.RenderLogLine(self.log[i][1], self.LogColors[self.log[i][0]], pos)
			if pos > hw.screenheight - screens.botborder:
				pygame.display.update()
				return (i + 1) if (i + 1) < len(self.log) else -1

		return -1


def ReportStatus(status, retain=True):
	if primaryBroker is not None:
		stat = json.dumps({'status': status, "uptime": time.time() - config.starttime,
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
			primaryBroker.Publish('set', payload='{"name":"System:GlobalLogViewTime","value":' + str(config.sysStore.LogStartTime) + '}', node='all')
