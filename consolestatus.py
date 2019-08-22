from collections import OrderedDict, namedtuple
import time
from datetime import datetime
from itertools import zip_longest
import functools
import configobj
import issuecommands

import pygame

import hw
import screen
import screenutil
import timers
import toucharea
from screens import __screens as screens
from utilfuncs import wc
from maintscreenbase import MaintScreenDesc
import logsupport
import keyspecs
import config


def Publish(topic, payload=None, node=hw.hostname, qos=1, retain=False, viasvr=False):
	# this gets replaced by actual Publish when MQTT starts up
	pass

nodes = OrderedDict()
noderecord = namedtuple('noderecord', ['status', 'uptime', 'error', 'rpttime', 'FirstUnseenErrorTime',
												   'GlobalLogViewTime', 'registered', 'versionname', 'versionsha',
												   'versiondnld', 'versioncommit', 'boottime', 'osversion', 'hw',
												   'APIXUfetches', 'queuetimemax24', 'queuetimemax24time',
												   'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
												   'queuetimemaxtime', 'daystartloops', 'queuedepthmax', 'queuetimemax',
												   'APIXUfetches24', 'queuedepthmaxtime'])

defaults = {k: v for (k, v) in zip_longest(noderecord._fields, (
	'unknown', 0, -2, 0, 0, 0, 0), fillvalue='unknown*')}

StatusDisp = None
Status = None
ShowHW = None
ShowVers = None
RespBuffer = []
RespNode = ''
RespRcvd = False
MsgSeq = 0


def SetUpConsoleStatus():
	global StatusDisp, ShowHW, ShowVers, Status
	if config.monitoringstatus:
		StatusDisp = StatusDisplayScreen()
		ShowHW = ShowVersScreen(True)
		ShowVers = ShowVersScreen(False)
		Status = MaintScreenDesc('Network Console Control',
								 OrderedDict([('curstat', (
									 'Networked Console Status',
									 functools.partial(screen.PushToScreen, StatusDisp, 'Maint'))),
											  ('hw', ('Console Hardware/OS',
													  functools.partial(screen.PushToScreen, ShowHW, 'Maint'))),
											  ('versions', ('Console Versions',
															functools.partial(screen.PushToScreen, ShowVers, 'Maint'))),
											  ('cmds', ('Issue Network Commands', GenGoNodeCmdScreen)),
											  ('return', ('Return', screen.PopScreen))]))
		StatusDisp.userstore.ReParent(Status)
		ShowVers.userstore.ReParent(Status)
		ShowHW.userstore.ReParent(Status)
		return Status
	else:
		return None

def NewNode(nd):
	nodes[nd] = noderecord(**defaults)


def GenGoNodeCmdScreen():
	IssueCmds = CommandScreen()
	IssueCmds.userstore.ReParent(Status)
	screen.PushToScreen(IssueCmds, 'Maint')

def UpdateStatus(nd, stat):
	if nd not in nodes: NewNode(nd)
	nodes[nd] = nodes[nd]._replace(**stat)


def GotResp(nd, errs):
	global ErrorBuffer, ErrorNode, RespRcvd
	ErrorBuffer = errs
	ErrorNode = nd
	RespRcvd = True


def status_interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	return "{} dys {:>02d}:{:>02d}:{:>02d}".format(d, h, m, s)


class ShowVersScreen(screen.BaseKeyScreenDesc):
	def __init__(self, showhw):
		self.showhw = showhw
		nm = 'HW=Status' if showhw else 'SW Versions'
		screen.BaseKeyScreenDesc.__init__(self, None, nm)
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}

	def InitDisplay(self, nav):
		super(ShowVersScreen, self).InitDisplay(nav)
		hw.screen.fill(wc(self.BackgroundColor))
		landfont = 15
		if hw.portrait:
			pass
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'  Node       ', landfont, 'white', False,
				FitLine=False)
		linestart = 40
		hw.screen.blit(header, (10, 20))
		for nd, ndinfo in nodes.items():
			offline = ' (offline)' if ndinfo.status in ('dead', 'unknown') else ' '
			if self.showhw:
				ln, _, _ = screenutil.CreateTextBlock(
					["{:12.12s} {} {}".format(nd, ndinfo.hw.replace('\00', ''), offline),
					 '             {}'.format(ndinfo.osversion.replace('\00', ''))], landfont, 'white', False)
			else:
				ln, _, _ = screenutil.CreateTextBlock(["{:12.12s} ({}) of {} {}".format(nd, ndinfo.versionname.replace(
					'\00', ''), ndinfo.versioncommit, offline),
													   '             Downloaded: {}'.format(ndinfo.versiondnld)],
													  landfont, 'white', False)
			hw.screen.blit(ln, (10, linestart))
			linestart += 2.5 * landfont
		pygame.display.update()


class StatusDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		screen.BaseKeyScreenDesc.__init__(self, None, 'ConsolesStatus')
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}
		self.T = None

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)
		self.T.cancel()

	def InitDisplay(self, nav):
		super(StatusDisplayScreen, self).InitDisplay(nav)
		self.T = timers.RepeatingPost(1, False, True, 'StatusDisplay', proc=self.ShowStatus)
		self.ShowStatus('none')

	def ShowStatus(self, ign):  # todo  portrait, no MQTT case
		if self.T.finished.is_set():
			return
		hw.screen.fill(wc(self.BackgroundColor))
		landfont = 17
		portfont = 17
		tm, ht, wd = screenutil.CreateTextBlock('{}'.format(time.strftime('%c')), landfont, 'white', False,
												FitLine=False)
		hw.screen.blit(tm, (10, 20))
		if hw.portrait:
			header, ht, wd = screenutil.CreateTextBlock(
				['     Node       Status   QMax E', '-->    Uptime            Last Boot'], portfont, 'white', False)
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'     Node       Status   QMax E       Uptime            Last Boot', landfont, 'white', False)
		linestart = 60 + int(ht * 1.2)
		hw.screen.blit(header, (10, 60))
		for nd, ndinfo in nodes.items():
			if ndinfo.maincyclecnt == 'unknown*':
				stat = ndinfo.status
				qmax = '     '
			else:
				stat = '{} cyc'.format(ndinfo.maincyclecnt) if ndinfo.status in ('idle', 'active') else ndinfo.status
				qmax = '{:4.2f} '.format(ndinfo.queuetimemax24)
			active = '*' if ndinfo.status == 'active' else ' '

			if ndinfo.status in ('dead', 'unknown'):
				cstat = "{:20.20s}".format(' ')
			else:
				cstat = ' ' if ndinfo.error == -1 else '?' if ndinfo.error == -1 else '*'
				cstat = cstat + "   {:>14.14s}  ".format(status_interval_str(ndinfo.uptime))
			if ndinfo.boottime == 0:
				bt = "{:^17.17}".format('unknown')
			else:
				bt = "{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(ndinfo.boottime))
			age = time.time() - ndinfo.rpttime if ndinfo.rpttime != 0 else 0
			# if age > 180:  # seconds?  todo use to determine likel#y powerfail case
			#	print(' (old:{})'.format(age))
			#	print('Boottime: {}'.format(ndinfo.boottime))
			# else:
			#	print()

			if hw.portrait:
				pass
			else:
				ln, ht, wd = screenutil.CreateTextBlock(
					'{:12.12s}{}{:10.10s} {}{} {}'.format(nd, active, stat, qmax, cstat, bt), landfont, 'white',
					False)
				hw.screen.blit(ln, (20, linestart))
				linestart += int(ht * 1.2)

		pygame.display.update()


class CommandScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		screen.BaseKeyScreenDesc.__init__(self, None, 'StatusCmdScreen', SingleUse=True)
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.SetScreenTitle('Remote Consoles', self.TitleFontSize, 'white')
		self.FocusNode = ''
		butht = 60
		butwidth = int(self.useablehorizspace / 2 * 0.9)
		butcenterleft = self.starthorizspace + int(self.useablehorizspace / 4)
		butcenterright = butcenterleft + int(self.useablehorizspace / 2)
		vt = self.startvertspace + butht // 2
		self.Keys = OrderedDict([('All', toucharea.ManualKeyDesc(self, 'All', label=('All',), bcolor='red',
																 charcoloron='white', charcoloroff='white',
																 center=(butcenterleft, vt), size=(butwidth, butht),
																 proc=functools.partial(self.ShowCmds,
																						'*')))])  # todo figure out how to only have relevant commands for all

		odd = False
		for nd, ndinfo in nodes.items():
			offline = ndinfo.status in ('dead', 'unknown')
			bcolor = 'grey' if offline else 'darkblue'
			usecenter = butcenterleft if odd else butcenterright
			self.Keys[nd] = toucharea.ManualKeyDesc(self, nd, label=(nd,), bcolor=bcolor, charcoloron='white',
													charcoloroff='white', center=(usecenter, vt),
													size=(butwidth, butht),
													proc=None if offline else functools.partial(self.ShowCmds, nd))
			if not odd: vt += butht + 3
			odd = not odd
		self.Keys['back'] = toucharea.ManualKeyDesc(self, 'Back', label=('Back',), bcolor='green', charcoloron='white',
													charcoloroff='white',
													center=(butcenterleft if odd else butcenterright, vt),
													size=(butwidth, butht), proc=screen.PopScreen)

		Cmds = configobj.ConfigObj(
			{'KeyCharColorOn': 'black', 'KeyColor': 'maroon', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'],
			 'DimTO': 60,
			 'PersistTO': 5, 'ScreenTitle': 'Placeholder'})

		for cmd, action in issuecommands.cmdcalls.items():
			if issuecommands.Where.RemoteMenu in action.where:
				DN = action.DisplayName.split(' ')
				Cmds[cmd] = {"type": "PROC", "ProcName": 'Command' + cmd, "label": DN, "Verify": action.Verify}
				if action.simple:
					keyspecs.internalprocs['Command' + cmd] = functools.partial(self.IssueSimpleCmd, cmd)
					Cmds[cmd]['MQTTInterest'] = 'True'
				else:
					keyspecs.internalprocs['Command' + cmd] = functools.partial(self.IssueComplexCmd, cmd)

		self.CmdListScreen = screens.screentypes["Keypad"](Cmds, 'CmdListScreen', parentscreen=self)
		self.CmdListScreen.SetScreenTitle('Commands', self.TitleFontSize, 'white')

	def IssueSimpleCmd(self, cmd, Key=None):
		global MsgSeq
		# todo bind with param for all the simple issues, sep proc for viewing errors which loops waiting buffer then goes to screen
		print("Issue simple cmd: {} to {}".format(cmd, self.FocusNode))
		MsgSeq += 1
		config.MQTTBroker.Publish('cmd', '{}|{}|{}'.format(cmd, hw.hostname, MsgSeq), self.FocusNode)
		self.CmdListScreen.AddToHubInterestList(config.MQTTBroker, cmd, Key)

		Key.State = False
		Key.PaintKey()
		pygame.display.update()

	def IssueComplexCmd(self, cmd):
		# todo bind with param for all the simple issues, sep proc for viewing errors which loops waiting buffer then goes to screen
		print("Issue complex cmd: {} to {}".format(cmd, self.FocusNode))

	def DisplayRecentErrors(self):
		print('Get recent errors from: {}'.format(self.FocusNode))

	def ShowCmds(self, nd):
		self.FocusNode = nd
		for key in self.CmdListScreen.Keys.values():
			key.State = True
		self.CmdListScreen.SetScreenTitle('Command to {}'.format(nd), self.TitleFontSize, 'white', force=True)
		screen.PushToScreen(self.CmdListScreen, newstate='Maint')

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)
		if not viaPush: self.CmdListScreen.userstore.DropStore()

	def RequestErrors(self, nd):
		global ErrorBuffer, ErrorNode, ErrorsRcvd
		ErrorsRcvd = False
		logsupport.primaryBroker.Publish('cmd', node=nd, payload='geterrors')

	def InitDisplay(self, nav):
		super(CommandScreen, self).InitDisplay(nav)
		# hw.screen.fill(wc(self.BackgroundColor))  todo junk?
		landfont = 15
		if hw.portrait:
			pass
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'  Node       ', landfont, 'white', False)
		pygame.display.update()
