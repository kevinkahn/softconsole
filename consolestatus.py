from collections import OrderedDict, namedtuple
import time
from datetime import datetime
import functools
import configobj
import issuecommands
import supportscreens
import json
import copy

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
import stats

import collections.abc


def update(d, u):
	for k, v in u.items():
		if isinstance(v, collections.abc.Mapping):
			d[k] = update(d.get(k, {}), v)
		else:
			d[k] = v
	return d


# def Publish(topic, payload=None, node=hw.hostname, qos=1, retain=False, viasvr=False):
#	# this gets replaced by actual Publish when MQTT starts up
#	pass



EmptyNodeRecord = {'hw': 'unknown*', 'osversion': 'unknown*', 'boottime': 'unknown*', "versioncommit": 'unknown*',
				   'versiondnld': 'unknown*', 'versionsha': 'unknown*', 'versionname': 'unknown*',
				   'registered': 0, "FirstUnseenErrorTime": 0, 'rpttime': 0, 'error': -2, "uptime": 0,
				   'status': 'unknown', 'stats': {'System': {}}}


Nodes = OrderedDict()

heldstatus = ''

# Performance info

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
	if config.mqttavailable:
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
											  ('cmds', ('Issue Network Commands', GenGoNodeCmdScreen))]), Clocked=1)
		StatusDisp.userstore.ReParent(Status)
		ShowVers.userstore.ReParent(Status)
		ShowHW.userstore.ReParent(Status)
		return Status
	else:
		return None



def GenGoNodeCmdScreen():
	IssueCmds = CommandScreen()
	IssueCmds.userstore.ReParent(Status)
	screen.PushToScreen(IssueCmds, 'Maint')


def UpdateNodeStatus(nd, stat):
	try:
		if nd not in Nodes: Nodes[nd] = copy.deepcopy(EmptyNodeRecord)

		# handle old style records
		if not 'registered' in stat and not 'stats' in stat:
			tempSys = {'stats': {'System': {}}}
			for nodestat in (
					'queuetimemax24', 'queuetimemax24time', 'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
					'queuetimemaxtime', 'queuedepthmax', 'queuetimemax', 'queuedepthmaxtime'):
				tempSys['stats']['System'][nodestat] = stat[nodestat]
				del stat[nodestat]
			update(Nodes[nd], tempSys)

		update(Nodes[nd], stat)

		t = False
		for nd, ndinfo in Nodes.items():
			if ndinfo['status'] not in ('dead', 'unknown') and nd != hw.hostname and ndinfo['error'] != -1:
				t = True
				break
		config.sysStore.NetErrorIndicator = t
	except Exception as E:
		logsupport.Logs.Log('UpdtStat {}'.format(E))


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
	def __init__(self, showhw, Clocked=0):
		self.showhw = showhw
		nm = 'HW Status' if showhw else 'SW Versions'
		super().__init__(None, nm, Clocked=Clocked)
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}

	def InitDisplay(self, nav):  # todo fix for specific repaint
		super(ShowVersScreen, self).InitDisplay(nav)
		hw.screen.fill(wc(self.BackgroundColor))
		fontsz = 10 if hw.portrait else 17
		header, ht, wd = screenutil.CreateTextBlock('  Node       ', fontsz, 'white', False, FitLine=False)
		linestart = 40
		hw.screen.blit(header, (10, 20))
		for nd, ndinfo in Nodes.items():
			offline = ' (offline)' if ndinfo['status'] in ('dead', 'unknown') else ' '
			ndln = "{:12.12s} ".format(nd)
			if self.showhw:
				ln1 = "{} {}".format(ndinfo['hw'].replace('\00', ''), offline)
				ln2 = '{}'.format(ndinfo['osversion'].replace('\00', ''))
			else:
				ln1 = "({}) of {} {}".format(nd, ndinfo['versionname'].replace('\00', ''), ndinfo['versioncommit'],
											 offline)
				ln2 = "Downloaded: {}".format(ndinfo['versiondnld'])

			if hw.portrait:
				ln, ht, _ = screenutil.CreateTextBlock([ndln, '  ' + ln1, '  ' + ln2], fontsz, 'white', False)
				pass
			else:
				ln, ht, _ = screenutil.CreateTextBlock([ndln + ln1, '             ' + ln2], fontsz, 'white', False)
			hw.screen.blit(ln, (10, linestart))
			linestart += ht + fontsz // 2
		pygame.display.update()


class StatusDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self, Clocked=0):
		super().__init__(None, 'ConsolesStatus', Clocked=Clocked)
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}
		self.T = None

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)
		self.T.cancel()

	def InitDisplay(self, nav): # todo fix for specific repaint
		super(StatusDisplayScreen, self).InitDisplay(nav)
		self.T = timers.RepeatingPost(1, False, True, 'StatusDisplay', proc=self.ShowStatus)
		self.ShowStatus('none')

	def ShowStatus(self, ign):  # todo  portrait, no MQTT case
		if self.T.finished.is_set():
			return
		hw.screen.fill(wc(self.BackgroundColor))
		fontsz = 10 if hw.portrait else 17
		tm, ht, wd = screenutil.CreateTextBlock('{}'.format(time.strftime('%c')), fontsz, 'white', False,
												FitLine=False)
		hw.screen.blit(tm, (10, 20))
		if hw.portrait:
			header, ht, wd = screenutil.CreateTextBlock(
				['    Node       Status   QMax E', '-->    Uptime/Last Boot'], fontsz, 'white', False)
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'     Node       Status   QMax E       Uptime            Last Boot', fontsz, 'white', False)
		linestart = 60 + int(ht * 1.2)
		hw.screen.blit(header, (10, 60))
		for nd, ndinfo in Nodes.items():
			try:
				statinfo = Nodes[nd]['stats']['System']
				if statinfo['maincyclecnt'] == 'unknown*':
					stat = ndinfo['status']
					qmax = '     '
				else:
					stat = '{} cyc'.format(statinfo['maincyclecnt']) if ndinfo['status'] in (
						'idle', 'active') else ndinfo['status']
					qmax = '{:4.2f} '.format(statinfo['queuetimemax24'])
				active = '*' if ndinfo['status'] == 'active' else ' '
				if ndinfo['status'] in ('dead', 'unknown'):
					estat = ''
					cstat = "{:14.14s}".format(' ')
				else:
					estat = ' ' if ndinfo['error'] == -1 else '?' if ndinfo['error'] == -1 else '*'
					cstat = " {:>15.15s}".format(status_interval_str(ndinfo['uptime']))

				if ndinfo['boottime'] == 0:
					bt = "{:^19.19}".format('unknown')
				else:
					bt = "{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(ndinfo['boottime']))
				age = time.time() - ndinfo['rpttime'] if ndinfo['rpttime'] != 0 else 0

				if hw.portrait:
					ln, ht, wd = screenutil.CreateTextBlock(
						['{:12.12s}{}{:10.10s} {}{}'.format(nd, active, stat, qmax, estat),
						 "  {}/{}".format(cstat, bt)],
						fontsz, 'white', False)
				else:
					ln, ht, wd = screenutil.CreateTextBlock(
						'{:12.12s}{}{:10.10s} {}{}  {}   {}'.format(nd, active, stat, qmax, estat, cstat, bt), fontsz,
						'white', False)
				hw.screen.blit(ln, (20, linestart))
				linestart += int(ht * 1.2)
			except Exception as E:
				logsupport.Logs.Log('Error displaying node status for {} Exc: {}'.format(nd, E),
									severity=logsupport.ConsoleWarning)

		pygame.display.update()


class CommandScreen(screen.BaseKeyScreenDesc):
	def __init__(self, Clocked=0):
		super().__init__(None, 'NodeCommandScreen', SingleUse=True, Clocked=Clocked)
		self.RespProcs = {'getlog': LogDisplay, 'geterrors': LogDisplay}
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.NavKeysShowing = True
		self.DefaultNavKeysShowing = True
		self.SetScreenTitle('Remote Consoles', self.TitleFontSize, 'white')
		self.FocusNode = ''
		self.NumNodes = 0
		butht = 60
		butwidth = int(self.useablehorizspace / 2 * 0.9)
		butcenterleft = self.starthorizspace + int(self.useablehorizspace / 4)
		butcenterright = butcenterleft + int(self.useablehorizspace / 2)
		vt = self.startvertspace + butht // 2
		self.Keys = OrderedDict([('All', toucharea.ManualKeyDesc(self, 'All', label=('All',), bcolor='red',
																 charcoloron='white', charcoloroff='white',
																 center=(butcenterleft, vt), size=(butwidth, butht),
																 proc=functools.partial(self.ShowCmds, 'Regular', '*'),
																 procdbl=functools.partial(self.ShowCmds, 'Advanced',
																						   '*')
																 ))])

		odd = False
		for nd, ndinfo in Nodes.items():
			offline = ndinfo['status'] in ('dead', 'unknown')
			if not offline: self.NumNodes += 1
			if nd == hw.hostname: continue
			bcolor = 'grey' if offline else 'darkblue'
			usecenter = butcenterleft if odd else butcenterright
			self.Keys[nd] = toucharea.ManualKeyDesc(self, nd, label=(nd,), bcolor=bcolor, charcoloron='white',
													charcoloroff='white', center=(usecenter, vt),
													size=(butwidth, butht),
													proc=None if offline else functools.partial(self.ShowCmds,
																								'Regular', nd),
													procdbl=None if offline else functools.partial(self.ShowCmds,
																								   'Advanced', nd))
			if not odd: vt += butht + 3
			odd = not odd

		CmdProps = {'KeyCharColorOn': 'white', 'KeyColor': 'maroon', 'BackgroundColor': 'royalblue',
					'label': ['Maintenance'],
					'DimTO': 60, 'PersistTO': 5, 'ScreenTitle': 'Placeholder'}

		CmdSet = {'Regular': configobj.ConfigObj(CmdProps), 'Advanced': configobj.ConfigObj(CmdProps)}

		for cmd, action in issuecommands.cmdcalls.items():
			DN = action.DisplayName.split(' ')
			if issuecommands.Where.RemoteMenu in action.where or issuecommands.Where.RemoteMenuAdv in action.where:
				whichscreen = 'Regular' if issuecommands.Where.RemoteMenu in action.where else "Advanced"
				keyspecs.internalprocs['Command' + cmd] = functools.partial(self.IssueSimpleCmd, cmd)
				if action.simple:
					CmdSet[whichscreen][cmd] = {"type": "REMOTEPROC", "ProcName": 'Command' + cmd, "label": DN,
								 "Verify": action.Verify}
				else:
					CmdSet[whichscreen][cmd] = {"type": "REMOTECPLXPROC", "ProcName": 'Command' + cmd, "label": DN,
								 "Verify": action.Verify, "EventProcName": 'Commandresp' + cmd}
					keyspecs.internalprocs['Commandresp' + cmd] = self.RespProcs[cmd]

		self.entered = ''
		self.CmdListScreens = {}
		for t, s in CmdSet.items():
			self.CmdListScreens[t] = screens.screentypes["Keypad"](s, 'CmdListScreen' + t, parentscreen=self, Clocked=1)

	# self.CmdListScreens[t].SetScreenTitle(t + ' Commands', self.TitleFontSize, 'white', force=True)

	def IssueSimpleCmd(self, cmd, Key=None):
		global MsgSeq
		MsgSeq += 1
		Key.Seq = MsgSeq
		if self.FocusNode == '*':
			Key.ExpectedNumResponses = self.NumNodes
			config.MQTTBroker.Publish('cmd', '{}|{}|{}'.format(cmd, hw.hostname, MsgSeq), 'all')
		else:
			Key.ExpectedNumResponses = 1
			config.MQTTBroker.Publish('cmd', '{}|{}|{}'.format(cmd, hw.hostname, MsgSeq), self.FocusNode)
		self.CmdListScreens[self.entered].AddToHubInterestList(config.MQTTBroker, cmd, Key)

	def ShowCmds(self, cmdset, nd):
		self.entered = cmdset
		self.FocusNode = nd
		self.CmdListScreens[cmdset].SetScreenTitle('{} Commands for {}'.format(cmdset, self.FocusNode),
												   self.TitleFontSize, 'white', force=True)
		for key in self.CmdListScreens[cmdset].Keys.values():
			key.State = True
			key.UnknownState = False if nd != '*' else issuecommands.cmdcalls[key.name].notgroup
		screen.PushToScreen(self.CmdListScreens[cmdset], newstate='Maint')

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)
		if not viaPush:
			for n, s in self.CmdListScreens.items():
				s.DeleteScreen()

	def PopOver(self):
		super().PopOver()
		for n, s in self.CmdListScreens.items():
			s.DeleteScreen()

	def RequestErrors(self, nd):
		global ErrorBuffer, ErrorNode, ErrorsRcvd
		ErrorsRcvd = False
		logsupport.primaryBroker.Publish('cmd', node=nd, payload='geterrors')

	def InitDisplay(self, nav): # todo fix for specific repaint
		super(CommandScreen, self).InitDisplay(nav)
		landfont = 15
		if hw.portrait:
			pass
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'  Node       ', landfont, 'white', False)
		pygame.display.update()


def PickStartingSpot():
	return 0


def PageTitle(pageno, itemnumber, node='', loginfo=None):
	if len(loginfo) > itemnumber:
		return "{} Log from {}           Page: {}".format(node, loginfo[itemnumber][2], pageno), True
	else:
		return "{} No more entries        Page: {}".format(node, pageno), False


def LogDisplay(evnt):
	p = supportscreens.PagedDisplay('remotelog', PickStartingSpot,
									functools.partial(logsupport.LineRenderer, uselog=evnt.value),
									functools.partial(PageTitle, node=evnt.respfrom, loginfo=evnt.value),
									config.sysStore.LogFontSize, 'white')
	p.singleuse = True
	screen.PushToScreen(p)


def ReportStatus(status, retain=True, hold=0):
	# held: 0 normal status report, 1 set an override status to be held, 2 clear and override status
	global heldstatus
	if hold == 1:
		heldstatus = status
	elif hold == 2:
		heldstatus = ''

	if logsupport.primaryBroker is not None:
		stattoreport = {'stats': stats.GetReportables()[1]}
		stattoreport.update({'status': status if heldstatus == '' else heldstatus,
							 "uptime": time.time() - config.sysStore.ConsoleStartTime,
							 "error": config.sysStore.ErrorNotice, 'rpttime': time.time(),
							 "FirstUnseenErrorTime": config.sysStore.FirstUnseenErrorTime,
							 'boottime': hw.boottime})  # rereport this because on powerup first NTP update can be after console starts
		stat = json.dumps(stattoreport)

		logsupport.primaryBroker.Publish(node=hw.hostname, topic='status', payload=stat, retain=retain, qos=1,
										 viasvr=True)


issuecommands.ReportStatus = ReportStatus
logsupport.ReportStatus = ReportStatus
