import requests

import hw
import screen
import config
import debug
import logsupport
import screens.__screens as screens
from logsupport import ConsoleWarning
import screenutil
import pygame
import toucharea
import supportscreens
import functools
import timers


# noinspection PyUnusedLocal
class OctoPrintScreenDesc(screen.BaseKeyScreenDesc):
	# todo switch to screen title
	def __init__(self, screensection, screenname):
		screen.ScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "New OctoPrintScreenDesc ", screenname)
		self.JobKeys = {}
		self.files = []
		self.filepaths = []
		self.PowerKeys = {}
		self.Subscreen = -1

		self.PollTimer = timers.RepeatingPost(5.0,paused=True,start=True,name=self.name+'-Poll',proc=self.ShowScreen)

		screen.IncorporateParams(self, 'OctoPrint', {'KeyColor'}, screensection)
		screen.AddUndefaultedParams(self, screensection, address='', apikey='')
		self.title, th, self.tw = screenutil.CreateTextBlock(self.name, hw.screenheight / 12, self.CharColor, True) #todo switch to new screen sizing for title
		self.titlespace = th + hw.screenheight / 32
		useablescreenheight = hw.screenheight - screens.topborder - screens.botborder - self.titlespace
		ctlpos = useablescreenheight / 5
		ctlhgt = int(ctlpos * .9)
		self.head = {"X-Api-Key": self.apikey}
		self.url = 'http://' + self.address + ':5000'
		retp = self.OctoGet('connection')
		if retp.status_code != 200:
			logsupport.Logs.Log('Access to OctoPrint denied: ', retp.text, severity=logsupport.ConsoleWarning)

		self.PowerKeys['printeron'] = toucharea.ManualKeyDesc(self, 'PowerOn', ['Power On'], self.KeyColor,
															  self.CharColor, self.CharColor,
															  center=(hw.screenwidth // 4, ctlpos * 4),
															  size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															  proc=functools.partial(self.Power, 'printeron'))
		self.PowerKeys['printeroff'] = toucharea.ManualKeyDesc(self, 'PowerOff', ['Power Off'], self.KeyColor,
															   self.CharColor, self.CharColor,
															   center=(3 * hw.screenwidth // 4, ctlpos * 4),
															   size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															   proc=functools.partial(self.Power, 'printeroff'))
		self.PowerKeys['connect'] = toucharea.ManualKeyDesc(self, 'Connect', ['Connect'], self.KeyColor,
															self.CharColor, self.CharColor,
															center=(hw.screenwidth // 4, ctlpos * 5),
															size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															proc=functools.partial(self.Connect, 'connect'))
		self.PowerKeys['disconnect'] = toucharea.ManualKeyDesc(self, 'Disconnect', ['Disconnect'], self.KeyColor,
															   self.CharColor, self.CharColor,
															   center=(3 * hw.screenwidth // 4, ctlpos * 5),
															   size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															   proc=functools.partial(self.Connect, 'disconnect'))
		self.PowerPlusKeys = self.PowerKeys.copy()
		self.PowerPlusKeys['Print'] = toucharea.ManualKeyDesc(self, 'Print', ['Print'], self.KeyColor,
															  self.CharColor, self.CharColor,
															  center=(hw.screenwidth // 2, ctlpos * 6),
															  size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															  proc=self.SelectFile)

		self.JobKeys['Cancel'] = toucharea.ManualKeyDesc(self, 'Cancel', ['Cancel'], self.KeyColor,
														 self.CharColor, self.CharColor,
														 center=(hw.screenwidth // 4, ctlpos * 5),
														 size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
														 proc=self.PreDoCancel, Verify=True)
		self.JobKeys['Pause'] = toucharea.ManualKeyDesc(self, 'Pause', ['Pause'], self.KeyColor,
														self.CharColor, self.CharColor,
														center=(3 * hw.screenwidth // 4, ctlpos * 5),
														size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
														proc=self.PreDoPause, Verify=True)
		self.VerifyScreenCancel = supportscreens.VerifyScreen(self.JobKeys['Cancel'], ('Cancel', 'Job'), ('Back',),
															  self.DoCancel,
															  screen, self.KeyColor, self.CharColor, self.CharColor,
															  True, None)
		self.VerifyScreenPause = supportscreens.VerifyScreen(self.JobKeys['Pause'], ('Pause', 'Job'), ('Back',),
															 self.DoCancel,
															 screen, self.KeyColor, self.CharColor, self.CharColor,
															 True, None)
		self.FileSubscreen = supportscreens.ListChooserSubScreen(self, 'FileList', 8, useablescreenheight,
																 self.titlespace,
																 self.FilePick)

	def FilePick(self, fileno):
		self.OctoPost('files/local/' + self.filepaths[fileno], senddata={'command': 'select'})
		self.OctoPost('job', senddata={'command': 'start'})
		self.Subscreen = -1
		self.ShowScreen()

	def OctoGet(self, item):
		try:
			r = requests.get(self.url + '/api/' + item, headers=self.head)
			return r
		except Exception as e:
			logsupport.Logs.Log('Bad octoprint get: ', repr(e), severity=ConsoleWarning)
			for i in range(5):
				# noinspection PyBroadException
				try:
					r = requests.get(self.url + '/api/' + item, headers=self.head)
					return r
				except:
					pass
		logsupport.Logs.Log("Permanent Octoprint Screen Error", severity=ConsoleWarning)
		raise ValueError


	def OctoPost(self, item, senddata):
		r = None
		try:
			r = requests.post(self.url + '/api/' + item, json=senddata, headers=self.head)
		except Exception as e:
			logsupport.Logs.Log("Octopost error {}".format(repr(e)), severity=ConsoleWarning)
		return r

	# noinspection PyUnusedLocal
	def Power(self, opt, presstype):
		_ = self.OctoPost('system/commands/custom/' + opt, {})
		self.PowerKeys[opt].BlinkKey(3)

	# noinspection PyUnusedLocal
	def Connect(self, opt, presstype):
		_ = self.OctoPost('connection', senddata={'command': opt})
		self.PowerKeys[opt].BlinkKey(3)

	def SelectFile(self, presstype):
		self.Subscreen = 1
		r = self.OctoGet('files/local')
		self.files = []
		self.filepaths = []
		files = r.json()['files']
		for f in files:
			self.files.append(f['name'])
			self.filepaths.append(f['path'])
		self.FileSubscreen.Initialize(self.files)
		# there was a task remove here for the poll = todo test it live
		self.ShowScreen()

	def PreDoCancel(self, presstype):
		self.VerifyScreenCancel.Invoke()

	def PreDoPause(self, presstype):
		self.VerifyScreenPause.Invoke()

	def DoCancel(self, go, presstype):
		if go:
			self.OctoPost('job', senddata={'command': 'cancel'})
			config.DS.SwitchScreen(self, 'Bright', config.DS.state, 'Verify Run ' + self.name)
		else:
			config.DS.SwitchScreen(self, 'Bright', config.DS.state, 'Verify Run ' + self.name)

	def DoPause(self, go, presstype):
		if go:
			self.OctoPost('job', senddata={'command': 'pause', 'action': 'toggle'})
			config.DS.SwitchScreen(self, 'Bright', config.DS.state, 'Verify Run ' + self.name)
		else:
			config.DS.SwitchScreen(self, 'Bright', config.DS.state, 'Verify Run ' + self.name)

	def InitDisplay(self, nav):
		super(OctoPrintScreenDesc, self).InitDisplay(nav)
		self.Subscreen = -1
		self.PollTimer.resume()
		self.ShowScreen()

	def ShowScreen(self,param=None):
		if not self.PollTimer.running.is_set():	return # handle race where poll refresh gets posted just as Maint screen comes up
		if self.Subscreen == -1:
			self.ShowControlScreen()
		elif self.Subscreen > 0:
			self.FileSubscreen.DisplayListSelect()
		config.screen.blit(self.title, ((hw.screenwidth - self.tw) / 2, 0))
		pygame.display.update()

	def ShowControlScreen(self):
		r = self.OctoGet('connection')
		OPstate = r.json()['current']['state']
		r = self.OctoGet('job').json()
		OPfile = r['job']['file']['name']
		if OPfile is None: OPfile = ''
		pct = r['progress']['completion']
		OPcomppct = '- Done ' if pct is None else '{0:.0%} Done '.format(pct / 100)
		tl = r['progress']['printTimeLeft']
		OPtimeleft = ' - Left' if tl is None else '{0:.0f} min'.format(tl / 60)
		statusblock, h, statusw = screenutil.CreateTextBlock([OPstate, OPfile, OPcomppct + OPtimeleft], 25,
															 self.CharColor, True)
		vpos = self.titlespace + h
		toblit = []

		if OPstate in ['Closed', 'Offline']:
			self.Keys = self.PowerKeys
		# self.ReInitDisplay()

		elif OPstate in ['Printing', 'Paused', 'Operational']:
			self.Keys = self.JobKeys if OPstate != 'Operational' else self.PowerPlusKeys
			# self.ReInitDisplay()
			r = self.OctoGet('printer').json()
			temp1 = r['temperature']['tool1']
			# noinspection PyBroadException
			try:
				OPtemp1 = 'Extruder: {0:.0f}/{1:.0f}'.format(temp1['actual'], temp1['target'])
			except:
				OPtemp1 = '-/-'
			bed = r['temperature']['bed']
			# noinspection PyBroadException
			try:
				OPbed = 'Bed: {0:.0f}/{1:.0f}'.format(bed['actual'], bed['target'])
			except:
				OPbed = '-/-'
			tool1, h, w = screenutil.CreateTextBlock([OPtemp1, OPbed], 25, self.CharColor, True)
			toblit.append((tool1, ((hw.screenwidth - w) // 2, vpos)))
			# config.screen.blit(tool1, ((config.screenwidth - w) // 2, vpos))
			vpos = vpos + h

		else:
			self.Keys = None
			# self.ReInitDisplay()
			print('Printer state: ', OPstate)
		# provide connect and power options

		self.ReInitDisplay()
		for i in toblit:
			config.screen.blit(i[0], i[1])
		config.screen.blit(statusblock, ((hw.screenwidth - statusw) // 2, self.titlespace))

	def ExitScreen(self):
		self.PollTimer.pause()


screens.screentypes["OctoPrint"] = OctoPrintScreenDesc
