import pygame
import webcolors
import sys
import traceback

wc = webcolors.name_to_rgb  # can't use the safe version from utilities due to import loop but this is only used with
# known color names

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


class Logs(object):
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
			if "Console.log." + str(config.MaxLogFiles) in q:
				os.remove('Console.log.' + str(config.MaxLogFiles))
			for i in range(config.MaxLogFiles - 1, 0, -1):
				if "Console.log." + str(i) in q:
					os.rename('Console.log.' + str(i), "Console.log." + str(i + 1))
			try:
				os.rename('Console.log', 'Console.log.1')
			except:
				pass
			self.disklogfile = open('Console.log', 'w')
			os.chmod('Console.log', 0o555)
			sys.stdout = self.disklogfile
			os.chdir(cwd)

	def Log(self, *args, **kwargs):
		"""
		params: args is one or more strings (like for print) and kwargs is severity=
		"""
		severity = kwargs.pop('severity', ConsoleInfo)
		tb = kwargs.pop('tb', True)
		if severity < config.LogLevel:
			return
		diskonly = kwargs.pop('diskonly', False)
		entry = "".join([unicode(i) for i in args])
		if not diskonly:
			self.log.append((severity, entry))
		if disklogging:
			self.disklogfile.write(time.strftime('%m-%d-%y %H:%M:%S')
								   + ' Sev: ' + str(severity) + " " + entry.encode('ascii',
																				   errors='backslashreplace') + '\n')
			if severity == ConsoleError and tb:
				# traceback.print_stack(file=self.disklogfile)
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

	def RenderLogLine(self, text, clr, pos):
		# odd logic below is to make sure that if an unbroken item would by itself exceed line length it gets forced out
		# thus avoiding an infinite loop
		text = re.sub('\s\s+', ' ', text)
		ltext = re.split('([ :,])', text)
		ltext.append('')
		ptext = []
		while len(ltext) > 1:
			ptext.append(ltext[0])
			del ltext[0]
			while 1:
				if len(ltext) == 0:
					break
				t = config.fonts.Font(config.LogFontSize).size(''.join(ptext) + ltext[0])[
					0]
				if t > config.screenwidth - 10:
					break
				else:
					ptext.append(ltext[0])
					del ltext[0]
			l = config.fonts.Font(config.LogFontSize).render(''.join(ptext), False, wc(clr))
			self.screen.blit(l, (10, pos))
			ptext = ["    "]
			pos = pos + config.fonts.Font(config.LogFontSize).get_linesize()
		pygame.display.update()
		return pos

	def RenderLog(self, backcolor, start=0):
		pos = 0
		config.screen.fill(wc(backcolor))
		for i in range(start, len(self.log)):
			pos = self.RenderLogLine(self.log[i][1], self.LogColors[self.log[i][0]], pos)
			if pos > config.screenheight - config.botborder:
				pygame.display.update()
				return (i + 1) if (i + 1) < len(self.log) else -1

		return -1
