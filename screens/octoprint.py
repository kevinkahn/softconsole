import requests
import screen
import config
import debug
import utilities
import logsupport
import screenutil
import pygame
import toucharea
import supportscreens
import functools
from eventlist import ProcEventItem


class OctoPrintScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		self.JobKeys = {}
		self.files = []
		self.filepaths = []
		self.PowerKeys = {}
		self.address = ''
		self.apikey = ''
		self.BackgroundColor = ''
		self.KeyColor = ''
		debug.debugPrint('Screen', "New OctoPrintScreenDesc ", screenname)
		screen.ScreenDesc.__init__(self, screensection, screenname)
		utilities.LocalizeParams(self, screensection, '-', 'KeyColor', 'BackgroundColor', address='', apikey='')
		self.title, th, self.tw = screenutil.CreateTextBlock(self.name, config.screenheight / 12, self.CharColor, True)
		self.titlespace = th + config.screenheight / 32
		useablescreenheight = config.screenheight - config.topborder - config.botborder - self.titlespace
		ctlpos = useablescreenheight / 5
		ctlhgt = int(ctlpos * .9)
		self.head = {"X-Api-Key": self.apikey}
		self.url = 'http://' + self.address + ':5000'
		retp = self.OctoGet('connection')
		self.PollStatus = ProcEventItem(id(self), 'octopoll', self.ShowScreen)
		if retp.status_code != 200:
			logsupport.Logs.Log('Access to OctoPrint denied: ', retp.text, severity=logsupport.ConsoleWarning)

		self.VerifyScreenCancel = supportscreens.VerifyScreen(self, ('Cancel', 'Job'), ('Back',), self.DoCancel,
															  screen, self.KeyColor, self.CharColor, self.CharColor,
															  True, None)
		self.VerifyScreenPause = supportscreens.VerifyScreen(self, ('Pause', 'Job'), ('Back',), self.DoCancel,
															 screen, self.KeyColor, self.CharColor, self.CharColor,
															 True, None)
		self.PowerKeys['printeron'] = toucharea.ManualKeyDesc(self.name, 'PowerOn', ['Power On'], self.KeyColor,
															  self.CharColor, self.CharColor,
															  center=(config.screenwidth // 4, ctlpos * 4),
															  size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
															  proc=functools.partial(self.Power, 'printeron'))
		self.PowerKeys['printeroff'] = toucharea.ManualKeyDesc(self.name, 'PowerOff', ['Power Off'], self.KeyColor,
															   self.CharColor, self.CharColor,
															   center=(3 * config.screenwidth // 4, ctlpos * 4),
															   size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
															   proc=functools.partial(self.Power, 'printeroff'))
		self.PowerKeys['connect'] = toucharea.ManualKeyDesc(self.name, 'Connect', ['Connect'], self.KeyColor,
															self.CharColor, self.CharColor,
															center=(config.screenwidth // 4, ctlpos * 5),
															size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
															proc=functools.partial(self.Connect, 'connect'))
		self.PowerKeys['disconnect'] = toucharea.ManualKeyDesc(self.name, 'Disconnect', ['Disconnect'], self.KeyColor,
															   self.CharColor, self.CharColor,
															   center=(3 * config.screenwidth // 4, ctlpos * 5),
															   size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
															   proc=functools.partial(self.Connect, 'disconnect'))
		self.PowerPlusKeys = self.PowerKeys.copy()
		self.PowerPlusKeys['Print'] = toucharea.ManualKeyDesc(self.name, 'Print', ['Print'], self.KeyColor,
															  self.CharColor, self.CharColor,
															  center=(config.screenwidth // 2, ctlpos * 6),
															  size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
															  proc=self.SelectFile)

		self.JobKeys['Cancel'] = toucharea.ManualKeyDesc(self.name, 'Cancel', ['Cancel'], self.KeyColor,
														 self.CharColor, self.CharColor,
														 center=(config.screenwidth // 4, ctlpos * 5),
														 size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
														 proc=self.PreDoCancel, Verify=True)
		self.JobKeys['Pause'] = toucharea.ManualKeyDesc(self.name, 'Pause', ['Pause'], self.KeyColor,
														self.CharColor, self.CharColor,
														center=(3 * config.screenwidth // 4, ctlpos * 5),
														size=(config.screenwidth // 3, ctlhgt), KOn='', KOff='',
														proc=self.PreDoPause, Verify=True)
		self.FileSubscreen = supportscreens.ListChooserSubScreen(self, 8, useablescreenheight, self.titlespace,
																 self.FilePick)

	def FilePick(self, fileno):
		self.OctoPost('files/local/' + self.filepaths[fileno], senddata={'command': 'select'})
		self.OctoPost('job', senddata={'command': 'start'})
		self.Subscreen = -1
		self.ShowScreen()

	def OctoGet(self, item):
		try:
			r = requests.get(self.url + '/api/' + item, headers=self.head)
		except Exception as e:
			print(repr(e))
		return r

	def OctoPost(self, item, senddata):
		try:
			r = requests.post(self.url + '/api/' + item, json=senddata, headers=self.head)
		except Exception as e:
			print(repr(e))
		return r

	def Power(self, opt, presstype):
		r = self.OctoPost('system/commands/custom/' + opt, {})
		self.PowerKeys[opt].BlinkKey(3)

	def Connect(self, opt, presstype):
		cmd = {'command': 'connect'} if opt else {'command': 'disconnect'}
		r = self.OctoPost('connection', senddata={'command': opt})
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
		config.DS.Tasks.RemoveTask(self.PollStatus)
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
		self.ShowScreen()

	def ShowScreen(self):
		config.DS.Tasks.RemoveTask(self.PollStatus)
		if self.Subscreen == -1:
			self.ShowControlScreen()
		elif self.Subscreen > 0:
			self.FileSubscreen.DisplayListSelect()
		config.screen.blit(self.title, ((config.screenwidth - self.tw) / 2, 0))
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
			try:
				OPtemp1 = 'Extruder: {0:.0f}/{1:.0f}'.format(temp1['actual'], temp1['target'])
			except:
				OPtemp1 = '-/-'
			bed = r['temperature']['bed']
			try:
				OPbed = 'Bed: {0:.0f}/{1:.0f}'.format(bed['actual'], bed['target'])
			except:
				OPbed = '-/-'
			tool1, h, w = screenutil.CreateTextBlock([OPtemp1, OPbed], 25, self.CharColor, True)
			toblit.append((tool1, ((config.screenwidth - w) // 2, vpos)))
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
		config.screen.blit(statusblock, ((config.screenwidth - statusw) // 2, self.titlespace))

		if self.PollStatus.OnList():
			# there are some races where this event is still on list (probably deleted) so can't reuse
			# but no reason to create lots of events if not needed
			config.DS.Tasks.RemoveTask(self.PollStatus)
			self.PollStatus = ProcEventItem(id(self), 'octopoll', self.ShowScreen)
		config.DS.Tasks.AddTask(self.PollStatus, 5)


config.screentypes["OctoPrint"] = OctoPrintScreenDesc
