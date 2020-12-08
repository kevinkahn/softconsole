from collections import OrderedDict
import time
from datetime import datetime
import functools
import configobj

from utils import displayupdate, hw
import issuecommands
from keys.keyutils import internalprocs
import screens.supportscreens as supportscreens
import json
import copy

from keyspecs import toucharea
from screens import __screens as screens, screen, screenutil
from utils.utilfuncs import wc, interval_str
from screens.maintscreenbase import MaintScreenDesc
import logsupport
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
											  ('cmds', ('Issue Network Commands', GenGoNodeCmdScreen))]))
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
	IssueCmds.DeleteScreen()


def UpdateNodeStatus(nd, stat):
	try:
		if nd not in Nodes: Nodes[nd] = copy.deepcopy(EmptyNodeRecord)

		# handle old style records
		if not 'registered' in stat and not 'stats' in stat:
			tempSys = {'stats': {'System': {}}}
			for nodestat in (
					'queuetimemax24', 'queuetimemax24time', 'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
					'queuetimemaxtime', 'queuedepthmax', 'queuetimemax', 'queuedepthmaxtime'):
				if nodestat in stat:
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
		logsupport.Logs.Log('UpdtStat {}'.format(repr(E)))


class ShowVersScreen(screen.BaseKeyScreenDesc):
	def __init__(self, showhw):
		self.showhw = showhw
		nm = 'HW Status' if showhw else 'SW Versions'
		super().__init__(None, nm)
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}

	def ScreenContentRepaint(self):
		hw.screen.fill(wc(self.BackgroundColor))
		fontsz = 10 if displayupdate.portrait else 17
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

			if displayupdate.portrait:
				ln, ht, _ = screenutil.CreateTextBlock([ndln, '  ' + ln1, '  ' + ln2], fontsz, 'white', False)
				pass
			else:
				ln, ht, _ = screenutil.CreateTextBlock([ndln + ln1, '             ' + ln2], fontsz, 'white', False)
			hw.screen.blit(ln, (10, linestart))
			linestart += ht + fontsz // 2

class StatusDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		super().__init__(None, 'ConsolesStatus')
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.Keys = {'return': toucharea.TouchPoint('back', (hw.screenwidth // 2, hw.screenheight // 2),
													(hw.screenwidth, hw.screenheight), proc=screen.PopScreen)}

	def ScreenContentRepaint(self):  # todo  portrait, no MQTT case
		hw.screen.fill(wc(self.BackgroundColor))
		fontsz = 10 if displayupdate.portrait else 17
		tm, ht, wd = screenutil.CreateTextBlock('{}'.format(time.strftime('%c')), fontsz, 'white', False,
												FitLine=False)
		hw.screen.blit(tm, (10, 20))
		if displayupdate.portrait:
			header, ht, wd = screenutil.CreateTextBlock(
				['    Node       Status   QMax E', '-->    Uptime/Last Boot'], fontsz, 'white', False)
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'     Node       Status   QMax E       Uptime            Last Boot', fontsz, 'white', False)
		linestart = 60 + int(ht * 1.2)
		hw.screen.blit(header, (10, 60))
		for nd, ndinfo in Nodes.items():
			try:
				if ndinfo['status'] in ('dead', 'unknown'):
					estat = ''
					cstat = "{:14.14s}".format(' ')
					stat = ndinfo['status']
					qmax = '     '
				else:
					estat = ' ' if ndinfo['error'] == -1 else '?' if ndinfo['error'] == -1 else '*'
					cstat = " {:>15.15s}".format(interval_str(ndinfo['uptime'], shrt=True))

					statinfo = Nodes[nd]['stats']['System']
					if 'maincyclecnt' not in statinfo or statinfo['maincyclecnt'] == 'unknown*':
						stat = ndinfo['status']
						qmax = '     '
					else:
						stat = '{} cyc'.format(statinfo['maincyclecnt']) if ndinfo['status'] in (
							'idle', 'active') else ndinfo['status']
						qmax = '{:4.2f} '.format(statinfo['queuetimemax24'])

				active = '*' if ndinfo['status'] == 'active' else ' '

				if ndinfo['boottime'] == 0:
					bt = "{:^19.19}".format('unknown')
				else:
					bt = "{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(ndinfo['boottime']))
				# age = time.time() - ndinfo['rpttime'] if ndinfo['rpttime'] != 0 else 0

				if displayupdate.portrait:
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
				logsupport.Logs.Log('Error displaying node status for {} Exc: {} Data: {}'.format(nd, E, ndinfo),
									severity=logsupport.ConsoleWarning)

		displayupdate.updatedisplay()


class CommandScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		super().__init__(None, 'NodeCommandScreen', SingleUse=True)
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
													procdbl=functools.partial(self.ShowCmds, 'Dead', nd) if offline
													else functools.partial(self.ShowCmds, 'Advanced', nd))
			if not odd: vt += butht + 3
			odd = not odd

		CmdProps = {'KeyCharColorOn': 'white', 'KeyColor': 'maroon', 'BackgroundColor': 'royalblue',
					'label': ['Maintenance'],
					'DimTO': 60, 'PersistTO': 5, 'ScreenTitle': 'Placeholder'}

		CmdSet = {'Regular': configobj.ConfigObj(CmdProps), 'Advanced': configobj.ConfigObj(CmdProps),
				  'Dead': configobj.ConfigObj(CmdProps)}

		for cmd, action in issuecommands.cmdcalls.items():
			DN = action.DisplayName.split(' ')
			if issuecommands.Where.RemoteMenu in action.where or issuecommands.Where.RemoteMenuAdv in action.where:
				whichscreen = 'Regular' if issuecommands.Where.RemoteMenu in action.where else "Advanced"
				internalprocs['Command' + cmd] = functools.partial(self.IssueSimpleCmd, cmd,
																   paramsetter=action.cmdparam)
				if action.simple:
					CmdSet[whichscreen][cmd] = {"type": "REMOTEPROC", "ProcName": 'Command' + cmd, "label": DN,
												"Verify": action.Verify}
				else:
					CmdSet[whichscreen][cmd] = {"type": "REMOTECPLXPROC", "ProcName": 'Command' + cmd, "label": DN,
												"Verify": action.Verify, "EventProcName": 'Commandresp' + cmd}
					internalprocs['Commandresp' + cmd] = self.RespProcs[cmd]
			elif issuecommands.Where.RemoteMenuDead in action.where:
				internalprocs['Command' + cmd] = functools.partial(self.IssueDeadCmd, cmd)
				CmdSet['Dead'][cmd] = {"type": "REMOTEPROC", "ProcName": 'Command' + cmd, "label": DN,
									   "Verify": action.Verify}
		self.entered = ''
		self.CmdListScreens = {}
		for t, s in CmdSet.items():
			self.CmdListScreens[t] = screens.screentypes["Keypad"](s, 'CmdListScreen' + t, parentscreen=self)

	def IssueSimpleCmd(self, cmd, Key=None, paramsetter=None):
		global MsgSeq
		MsgSeq += 1
		Key.Seq = MsgSeq
		if paramsetter is None:
			cmdsend = '{}|{}|{}'.format(cmd, hw.hostname, MsgSeq)
		else:
			cmdsend = '{}|{}|{}|{}'.format(cmd, hw.hostname, MsgSeq, paramsetter())

		if self.FocusNode == '*':
			Key.ExpectedNumResponses = self.NumNodes
			config.MQTTBroker.Publish('cmd', cmdsend, 'all')
		else:
			Key.ExpectedNumResponses = 1
			config.MQTTBroker.Publish('cmd', cmdsend, self.FocusNode)
		self.CmdListScreens[self.entered].AddToHubInterestList(config.MQTTBroker, cmd, Key)

	# noinspection PyUnusedLocal
	def IssueDeadCmd(self, cmd, Key=None):
		# local processing only for a command regarding a dead node
		if cmd == 'deletehistory':
			del Nodes[self.FocusNode]
			config.MQTTBroker.Publish('status', node=self.FocusNode, retain=True)
			config.MQTTBroker.Publish(self.FocusNode, node='all/nodes', retain=True)
			logsupport.Logs.Log("Purging network history of node {}".format(self.FocusNode))
		else:
			logsupport.Logs.Log('Internal error on dead node command: {} for {}'.format(cmd, self.FocusNode))

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

	'''
	def ScreenContentRepaint(self):  # todo ???
		landfont = 15
		if displayupdate.portrait:
			pass
		else:
			header, ht, wd = screenutil.CreateTextBlock(
				'  Node       ', landfont, 'white', False)
	'''

def PickStartingSpot():
	return 0


def PageTitle(pageno, itemnumber, node='', loginfo=None):
	if len(loginfo) > itemnumber:
		return "{} Log from {}           Page: {}      {}".format(node, loginfo[itemnumber][2], pageno,
																  time.strftime('%c')), True
	else:
		return "{} No more entries        Page: {}      {}".format(node, pageno, time.strftime('%c')), False


def LogDisplay(evnt):
	p = supportscreens.PagedDisplay('remotelog', PickStartingSpot,
									functools.partial(logsupport.LineRenderer, uselog=evnt.value),
									functools.partial(PageTitle, node=evnt.respfrom, loginfo=evnt.value),
									config.sysStore.LogFontSize, 'white')
	if evnt.value:
		issuecommands.lastseenlogmessage = (evnt.value[0][0], evnt.value[0][1])
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
