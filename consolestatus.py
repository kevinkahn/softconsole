from collections import OrderedDict, namedtuple
import time
from datetime import datetime
from itertools import zip_longest
import functools
import configobj
import issuecommands
import supportscreens

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
									   'registered', 'versionname', 'versionsha',
									   'versiondnld', 'versioncommit', 'boottime', 'osversion', 'hw',
									   'APIXUfetches', 'queuetimemax24', 'queuetimemax24time',
									   'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
									   'queuetimemaxtime', 'daystartloops', 'queuedepthmax', 'queuetimemax',
									   'APIXUfetches24', 'queuedepthmaxtime'])

defaults = {k: v for (k, v) in zip_longest(noderecord._fields, (
	'unknown', 0, -2, 0, 0, 0), fillvalue='unknown*')}

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
											  ('return', ('Return', screen.PopScreen))]), Clocked=1)
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
	# Handle cases where nodes are reporting status fields we are not tracking
	updts = [f for f in stat.keys()]
	for k in updts:
		if not hasattr(nodes[nd], k):
			del stat[k]
	nodes[nd] = nodes[nd]._replace(**stat)
	t = False
	for nd, ndinfo in nodes.items():
		if ndinfo.status not in ('dead', 'unknown') and nd != hw.hostname and ndinfo.error != -1:
			t = True
			break
	config.sysStore.NetErrorIndicator = t  # tempdel or (config.sysStore.ErrorNotice != -1)

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

	def InitDisplay(self, nav):
		super(ShowVersScreen, self).InitDisplay(nav)
		hw.screen.fill(wc(self.BackgroundColor))
		fontsz = 10 if hw.portrait else 17
		header, ht, wd = screenutil.CreateTextBlock('  Node       ', fontsz, 'white', False, FitLine=False)
		linestart = 40
		hw.screen.blit(header, (10, 20))
		for nd, ndinfo in nodes.items():
			offline = ' (offline)' if ndinfo.status in ('dead', 'unknown') else ' '
			ndln = "{:12.12s} ".format(nd)
			if self.showhw:
				ln1 = "{} {}".format(ndinfo.hw.replace('\00', ''), offline)
				ln2 = '{}'.format(ndinfo.osversion.replace('\00', ''))
			else:
				ln1 = "({}) of {} {}".format(nd, ndinfo.versionname.replace('\00', ''), ndinfo.versioncommit, offline)
				ln2 = "Downloaded: {}".format(ndinfo.versiondnld)
			# ln, ht, _ = screenutil.CreateTextBlock(["{:12.12s} ({}) of {} {}".format(nd, ndinfo.versionname.replace(
			#	'\00', ''), ndinfo.versioncommit, offline),
			#									   '             Downloaded: {}'.format(ndinfo.versiondnld)],
			#									  landfont, 'white', False)
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

	def InitDisplay(self, nav):
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
		for nd, ndinfo in nodes.items():
			if ndinfo.maincyclecnt == 'unknown*':
				stat = ndinfo.status
				qmax = '     '
			else:
				stat = '{} cyc'.format(ndinfo.maincyclecnt) if ndinfo.status in ('idle', 'active') else ndinfo.status
				qmax = '{:4.2f} '.format(ndinfo.queuetimemax24)
			active = '*' if ndinfo.status == 'active' else ' '

			if ndinfo.status in ('dead', 'unknown'):
				estat = ''
				cstat = "{:14.14s}".format(' ')
			else:
				estat = ' ' if ndinfo.error == -1 else '?' if ndinfo.error == -1 else '*'
				cstat = " {:>14.14s}  ".format(status_interval_str(ndinfo.uptime))
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
				ln, ht, wd = screenutil.CreateTextBlock(
					['{:12.12s}{}{:10.10s} {}{}'.format(nd, active, stat, qmax, estat), "  {} {}".format(cstat, bt)],
					fontsz, 'white', False)
			else:
				ln, ht, wd = screenutil.CreateTextBlock(
					'{:12.12s}{}{:10.10s} {}{}  {}/{}'.format(nd, active, stat, qmax, estat, cstat, bt), fontsz,
					'white', False)
			hw.screen.blit(ln, (20, linestart))
			linestart += int(ht * 1.2)

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
		# todo figure out how to only have relevant commands for all

		odd = False
		for nd, ndinfo in nodes.items():
			offline = ndinfo.status in ('dead', 'unknown')
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
			# print('Issue Group command {} to {} nodes'.format(cmd, self.NumNodes))
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
		# if not viaPush: self.CmdListScreens[self.entered].userstore.DropStore()  #tempdel - this should be replaced by an explicit screen kill
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

	def InitDisplay(self, nav):
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
