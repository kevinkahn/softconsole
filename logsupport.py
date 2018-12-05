import historybuffer
import pygame
import webcolors
import sys
import traceback
import json

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

LogLevel = 3

def StringLike(obj):
	return isinstance(obj, str)  # todo del


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
			self.disklogfile = open('Console.log', 'w')
			os.chmod('Console.log', 0o555)
			historybuffer.SetupHistoryBuffers(dirnm, maxf)
			os.chdir(cwd)

	def Log(self, *args, **kwargs):
		"""
		params: args is one or more strings (like for print) and kwargs is severity=
		"""
		severity = kwargs.pop('severity', ConsoleInfo)
		entrytime = kwargs.pop('entrytime', time.strftime('%m-%d-%y %H:%M:%S'))
		tb = kwargs.pop('tb', True)
		hb = kwargs.pop('hb', False)
		localonly = kwargs.pop('localonly', False)


		if severity < LogLevel:
			return
		diskonly = kwargs.pop('diskonly', False)
		#entry = "".join([unicode(i) for i in args])
		entry = ''
		for i in args:
			if StringLike(i):
				if not isinstance(i, str):
					entry = entry + i.encode('UTF-8', errors='backslashreplace')
				else:
					entry = entry + i
			else:
				entry = entry + str(i)

		if hb: historybuffer.DumpAll(entry, entrytime)


		if not diskonly:
			self.log.append((severity, entry, entrytime))
			if severity in [ConsoleWarning, ConsoleError]:
				if config.primaryBroker is not None and not localonly:
					config.primaryBroker.Publish1('errors', json.dumps(
						{'node': config.hostname, 'sev': severity, 'time': entrytime, 'entry': entry}), node='all')

			if severity in [ConsoleWarning, ConsoleError] and config.sysStore.ErrorNotice == -1:
				config.sysStore.FirstUnseenErrorTime = time.time()
				config.sysStore.ErrorNotice = len(self.log) - 1
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
		if self.livelog and not diskonly:
			if self.livelogpos == 0:
				config.screen.fill(wc('royalblue'))
			self.livelogpos = self.RenderLogLine(entry, self.LogColors[severity], self.livelogpos)
			if self.livelogpos > config.screenheight - config.botborder:
				time.sleep(1)
				self.livelogpos = 0
			pygame.display.update()

	def RenderLogLine(self, itext, clr, pos):
		# odd logic below is to make sure that if an unbroken item would by itself exceed line length it gets forced out
		# thus avoiding an infinite loop
		text = itext  # todo del
		# if isinstance(itext, str):
		#	try:
		#		text = itext.decode(encoding='UTF-8')  # unicode(v,'UTF-8')
		#	except AttributeError:
		#		text = itext
		# noinspection PyUnboundLocalVariable
		text = re.sub('\s\s+', ' ', text.rstrip())
		ltext = re.split('([ :,])', text)
		ltext.append('')
		ptext = []
		logfont = config.fonts.Font(config.sysStore.LogFontSize, face=config.monofont)
		while len(ltext) > 1:
			ptext.append(ltext[0])
			del ltext[0]
			while 1:
				if len(ltext) == 0:
					break
				t = logfont.size(''.join(ptext) + ltext[0])[0]
				if t > config.screenwidth - 10:
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
			if pos > config.screenheight - config.botborder:
				pygame.display.update()
				return (i + 1) if (i + 1) < len(self.log) else -1

		return -1
