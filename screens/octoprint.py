import functools

import pygame
import requests
import threading
import controlevents
import debug
import historybuffer
import hw
import logsupport
import screen
import screens.__screens as screens
import screenutil
import supportscreens
import timers
import toucharea
from logsupport import ConsoleWarning
from keyspecs import _resolvekeyname


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

		# status of printer
		self.OPstate = 'unknown'
		self.OPfile = ''
		self.OPcomppct = 'unknown'
		self.OPtimeleft = 'unknown'
		self.OPtemp1 = 'unknown'
		self.OPbed = 'unknown'
		self.ValidState = False


		self.PollTimer = timers.RepeatingPost(5.0, paused=True, start=True, name=self.name + '-Poll',
											  proc=self.RefreshOctoStatus)

		screen.IncorporateParams(self, 'OctoPrint', {'KeyColor'}, screensection)
		screen.AddUndefaultedParams(self, screensection, address='', apikey='', extruder='tool0', port='5000',
									pwrctl='')  # pwrctl = HASS:switch.prusa
		self.title, th, self.tw = screenutil.CreateTextBlock(self.name, hw.screenheight / 12, self.CharColor,
															 True)  # todo switch to new screen sizing for title

		if self.pwrctl != '':
			self.devname, self.pwrHub = _resolvekeyname(self.pwrctl, None)
		else:
			self.pwrHub = None
			self.devname = ''

		self.errornotice, th, self.errwid = screenutil.CreateTextBlock('Access Error', hw.screenheight / 12, self.CharColor, True) # todo fix for new vertspace
		self.titlespace = th + hw.screenheight / 32
		useablescreenheight = hw.screenheight - self.TopBorder - self.BotBorder - self.titlespace
		ctlpos = useablescreenheight / 5.5  # todo should lay out screen with real values computed
		ctlhgt = int(ctlpos * .9)
		self.head = {"X-Api-Key": self.apikey}
		self.url = 'http://' + self.address + ':' + self.port
		retp = self.OctoGet('connection')
		if retp.status_code != 200:
			logsupport.Logs.Log('Access to OctoPrint denied: ', retp.text, severity=logsupport.ConsoleWarning)

		self.PowerKeys['printeron'] = toucharea.ManualKeyDesc(self, 'PowerOn', ['Power On'], self.KeyColor,
															  'white', 'black',
															  #															  self.CharColor, self.CharColor,
															  center=(hw.screenwidth // 4, ctlpos * 4),
															  size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															  proc=functools.partial(self.Power, 'printeron'))
		self.PowerKeys['printeroff'] = toucharea.ManualKeyDesc(self, 'PowerOff', ['Power Off'], self.KeyColor,
															   'white', 'black',
															   #															   self.CharColor, self.CharColor,
															   center=(3 * hw.screenwidth // 4, ctlpos * 4),
															   size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															   proc=functools.partial(self.Power, 'printeroff'))
		self.PowerKeys['connect'] = toucharea.ManualKeyDesc(self, 'Connect', ['Connect'], self.KeyColor,
															'white', 'black',
															#															self.CharColor, self.CharColor,
															center=(hw.screenwidth // 4, ctlpos * 5),
															size=(hw.screenwidth // 3, ctlhgt), KOn='', KOff='',
															proc=functools.partial(self.Connect, 'connect'))
		self.PowerKeys['disconnect'] = toucharea.ManualKeyDesc(self, 'Disconnect', ['Disconnect'], self.KeyColor,
															   'white', 'black',
															   #															   self.CharColor, self.CharColor,
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
															  self.DoCancel, None,
															  screen, self.KeyColor, self.CharColor, self.CharColor,
															  True, None)
		self.VerifyScreenPause = supportscreens.VerifyScreen(self.JobKeys['Pause'], ('Pause', 'Job'), ('Back',),
															 self.DoCancel, None,
															 screen, self.KeyColor, self.CharColor, self.CharColor,
															 True, None)
		self.FileSubscreen = supportscreens.ListChooserSubScreen(self, 'FileList', 8, useablescreenheight,
																 self.titlespace,
																 self.FilePick)

	def FilePick(self, fileno):
		# called from file chooser screen todo - turn into a post to do work?
		self.OctoPost('files/local/' + self.filepaths[fileno], senddata={'command': 'select'})
		self.OctoPost('job', senddata={'command': 'start'})

	def OctoGet(self, item):
		try:
			historybuffer.HBNet.Entry('Octoprint get: {} from {}'.format(item, self.url))
			r = requests.get(self.url + '/api/' + item, headers=self.head)
			historybuffer.HBNet.Entry('Octoprint done with {}'.format(item))
			return r
		except Exception as e:
			logsupport.Logs.Log('Bad octoprint get: ', repr(e), severity=ConsoleWarning)
			for i in range(5):
				# noinspection PyBroadException
				try:
					historybuffer.HBNet.Entry('Octoprint retry')
					r = requests.get(self.url + '/api/' + item, headers=self.head)
					historybuffer.HBNet.Entry('Octoprint retry done')
					return r
				except:
					pass
		logsupport.Logs.Log("Permanent Octoprint Screen Error", severity=ConsoleWarning)
		raise ValueError

	def OctoPost(self, item, senddata):
		r = None
		try:
			historybuffer.HBNet.Entry('Octoprint post: {} of {}'.format(item, repr(senddata)))
			r = requests.post(self.url + '/api/' + item, json=senddata, headers=self.head)
			historybuffer.HBNet.Entry('Octoprint post done for {}'.format(item))
		except Exception as e:
			logsupport.Logs.Log("Octopost error {}".format(repr(e)), severity=ConsoleWarning)
		self.AsyncRefreshOctoStatus()
		return r

	# noinspection PyUnusedLocal
	def Power(self, opt):
		if self.pwrHub is None:
			_ = self.OctoPost('system/commands/custom/' + opt, {})
		else:
			self.pwrHub.GetNode(self.devname)[0].SendOnOffCommand(opt == 'printeron')
		self.PowerKeys[opt].ScheduleBlinkKey(5)

	# noinspection PyUnusedLocal
	def Connect(self, opt):
		_ = self.OctoPost('connection', senddata={'command': opt})
		self.PowerKeys[opt].ScheduleBlinkKey(5)

	def SelectFile(self):
		r = self.OctoGet('files/local')
		self.files = []
		self.filepaths = []
		files = r.json()['files']
		for f in files:
			self.files.append(f['name'])
			self.filepaths.append(f['path'])
		self.FileSubscreen.Initialize(self.files)
		screens.DS.SwitchScreen(self.FileSubscreen, 'Bright', 'Direct go to OctoPrint fileselect', push=True)

	def PreDoCancel(self):
		self.VerifyScreenCancel.Invoke()

	def PreDoPause(self):
		self.VerifyScreenPause.Invoke()

	def NoVerify(self):
		screens.DS.SwitchScreen(self, 'Bright', 'Verify Run ' + self.name)

	def DoCancel(self):
		self.OctoPost('job', senddata={'command': 'cancel'})
		screens.DS.SwitchScreen(self, 'Bright', 'Verify Run ' + self.name)

	def DoPause(self, go):
		self.OctoPost('job', senddata={'command': 'pause', 'action': 'toggle'})
		screens.DS.SwitchScreen(self, 'Bright', 'Verify Run ' + self.name)

	def ReInitDisplay(self):
		super(OctoPrintScreenDesc, self).ReInitDisplay()
		self.ShowScreen()

	def InitDisplay(self, nav):
		super(OctoPrintScreenDesc, self).InitDisplay(nav)
		self.AsyncRefreshOctoStatus()
		self.PollTimer.resume()
		self.ShowScreen()

	def ShowScreen(self, param=None):
		if not self.Active:    return  # handle race where poll refresh gets posted just as Maint screen comes up
		try:
			self.ShowControlScreen()
			hw.screen.blit(self.title, ((hw.screenwidth - self.tw) / 2, 0))
		except ValueError:
			hw.screen.blit(self.errornotice, ((hw.screenwidth - self.errwid) / 2, 30))
		hw.screen.blit(self.title, ((hw.screenwidth - self.tw) / 2, 0))
		pygame.display.update()

	def AsyncRefreshOctoStatus(self):
		T = threading.Thread(target=self.RefreshOctoStatus, daemon=True, name='OctoTrigRefresh')
		T.start()

	def RefreshOctoStatus(self, param=None):
		try:
			self.ValidState = False
			r = self.OctoGet('connection')
			self.OPstate = r.json()['current']['state']
			r = self.OctoGet('job').json()
			self.OPfile = r['job']['file']['name']
			if self.OPfile is None: self.OPfile = ''
			pct = r['progress']['completion']
			self.OPcomppct = '- Done ' if pct is None else '{0:.0%} Done '.format(pct / 100)
			tl = r['progress']['printTimeLeft']
			self.OPtimeleft = ' - Left' if tl is None else '{0:.0f} min'.format(tl / 60)

			if self.OPstate in ['Printing', 'Paused', 'Operational']:
				self.Keys = self.JobKeys if self.OPstate != 'Operational' else self.PowerPlusKeys
				r = self.OctoGet('printer').json()
				temp1 = r['temperature'][self.extruder]
				# noinspection PyBroadException
				try:
					self.OPtemp1 = 'Extruder: {0:.0f}/{1:.0f}'.format(temp1['actual'], temp1['target'])
				except:
					self.OPtemp1 = '-/-'
				bed = r['temperature']['bed']
				# noinspection PyBroadException
				try:
					self.OPbed = 'Bed: {0:.0f}/{1:.0f}'.format(bed['actual'], bed['target'])
				except:
					self.OPbed = '-/-'

			elif self.OPstate in ['Closed', 'Offline']:
				self.Keys = self.PowerKeys

			else:
				self.Keys = self.PowerKeys  # todo Error state case - should actually be some sort of reset

			self.ValidState = True
			controlevents.PostEvent(controlevents.ConsoleEvent(controlevents.CEvent.GeneralRepaint))
		except Exception as E:
			logsupport.Logs.Log('Error fetching OctoPrint status: {}'.format(repr(E)))


	def ShowControlScreen(self):

		toblit = []
		if self.ValidState:
			statusblock, h, statusw = screenutil.CreateTextBlock(
				[self.OPstate, self.OPfile, self.OPcomppct + self.OPtimeleft], 25,
															 self.CharColor, True)

			vpos = self.titlespace + h

			if self.OPstate in ['Printing', 'Paused', 'Operational']:
				tool1, h, w = screenutil.CreateTextBlock([self.OPtemp1, self.OPbed], 25, self.CharColor, True)
				toblit.append((tool1, ((hw.screenwidth - w) // 2, vpos)))
				# config.screen.blit(tool1, ((config.screenwidth - w) // 2, vpos))
				vpos = vpos + h

		else:
			statusblock, h, statusw = screenutil.CreateTextBlock(['Not Available', ], 25, self.CharColor, True)


		for i in toblit:
			hw.screen.blit(i[0], i[1])
		hw.screen.blit(statusblock, ((hw.screenwidth - statusw) // 2, self.titlespace))

	def ExitScreen(self):
		self.PollTimer.pause()


screens.screentypes["OctoPrint"] = OctoPrintScreenDesc
