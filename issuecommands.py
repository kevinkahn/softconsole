import json
import os
import threading
import subprocess
import functools
from dataclasses import dataclass
from ast import literal_eval

import githubutil as U
import logsupport
import historybuffer
import time
from logsupport import ConsoleWarning, ConsoleError, ConsoleInfo
from controlevents import PostEvent, ConsoleEvent, CEvent
import config
from collections import OrderedDict
from typing import Callable, Union
from enum import Enum

from stores import valuestore
from utils import hw
from utils.exitutils import MAINTEXIT, Exit_Screen_Message, MAINTRESTART, MAINTPISHUT, MAINTPIREBOOT, Exit, \
	REMOTERESTART, \
	REMOTEEXIT, REMOTEPISHUT, REMOTEPIREBOOT

fetcher = None  # type: Union[None, threading.Thread]

ReportStatus = None  # type: Union[Callable, None]

Nodes = OrderedDict()


def DeleteNode(nd):
	logsupport.Logs.Log('Deleting history of node {}'.format(nd))
	del Nodes[nd]


lastseenlogmessage = ''


# filled in by consolestatus to avoid dependency loop

def TempCheckSanity(Key, params):
	if Key is None and params is None:
		logsupport.Logs.Log('Internal Error: Both Command sources are None', severity=ConsoleError, tb=True, hb=True)


def FetchInProgress():
	global fetcher
	return fetcher is not None and fetcher.is_alive()


# todo further compress below to unify messagint
# noinspection PyUnusedLocal
def RestartConsole(params=None, Key=None, AutoVer=False):
	TempCheckSanity(Key, params)
	if not FetchInProgress():
		_SystemTermination('console restart', 'Console Restart', (MAINTRESTART, REMOTERESTART), Key, params)
	else:
		CommandResp(Key, 'nak', params, None)


def ShutConsole(params=None, Key=None):
	TempCheckSanity(Key, params)
	if not FetchInProgress():
		_SystemTermination('console shutdown', 'Console Shutdown', (MAINTEXIT, REMOTEEXIT), Key, params)
	else:
		CommandResp(Key, 'nak', params, None)


def ShutdownPi(params=None, Key=None):
	TempCheckSanity(Key, params)
	if not FetchInProgress():
		_SystemTermination('pi shutdown', "Pi Shutdown", (MAINTPISHUT, REMOTEPISHUT), Key, params)
	else:
		CommandResp(Key, 'nak', params, None)


def RebootPi(params=None, Key=None):
	TempCheckSanity(Key, params)
	if not FetchInProgress():
		_SystemTermination('pi reboot', "Pi Reboot", (MAINTPIREBOOT, REMOTEPIREBOOT), Key, params)
	else:
		CommandResp(Key, 'nak', params, None)


def _SystemTermination(statmsg, exitmsg, exitcode, Key, params):
	ReportStatus(statmsg)
	CommandResp(Key, 'ok', params, None)
	Exit_Screen_Message(exitmsg + ' Requested', ('Remote' if Key is None else 'Maintenance') + ' Request', exitmsg)
	config.terminationreason = ('remote' if Key is None else 'manual') + statmsg
	Exit(exitcode[1] if Key is None else exitcode[0])


def DoDelayedAction(evnt):  # only for autover
	PostEvent(ConsoleEvent(CEvent.RunProc, name='DelayedRestart', proc=evnt.action))


def CommandResp(Key, success, params, value):
	if Key is not None:
		if success == 'ok':
			Key.ScheduleBlinkKey(5)
		else:
			Key.FlashNo(5)
	else:
		config.MQTTBroker.CommandResponse(success, params[0], params[1], params[2], value)


def Get(nm, target, params, Key):
	global fetcher
	TempCheckSanity(Key, params)
	if not FetchInProgress():
		fetcher = threading.Thread(name=nm, target=target, daemon=True)
		fetcher.start()
		CommandResp(Key, 'ok', params, None)
	else:
		CommandResp(Key, 'busy', params, None)


def GetStable(params=None, Key=None):
	Get('FetchStableRemote', fetch_stable, params, Key)


def GetBeta(params=None, Key=None):
	Get('FetchBetRemote', fetch_beta, params, Key)


def GetDev(params=None, Key=None):
	Get('FetchDevRemote', fetch_dev, params, Key)


def UseStable(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('echo stable > /home/pi/versionselector', shell=True)
	CommandResp(Key, 'ok', params, None)


def UseBeta(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('echo beta > /home/pi/versionselector', shell=True)
	CommandResp(Key, 'ok', params, None)


def UseDev(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('echo dev > /home/pi/versionselector', shell=True)
	CommandResp(Key, 'ok', params, None)


def FreezeConfig(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('echo FROZEN > /home/pi/.freezeconfig', shell=True)
	CommandResp(Key, 'ok', params, None)


def UnfreezeConfig(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('rm /home/pi/.freezeconfig', shell=True)
	CommandResp(Key, 'ok', params, None)


def DumpHB(params=None, Key=None):
	TempCheckSanity(Key, params)
	entrytime = time.strftime('%m-%d-%y %H:%M:%S')
	historybuffer.DumpAll('Command Dump', entrytime)
	CommandResp(Key, 'ok', params, None)


def EchoStat(params=None, Key=None):
	TempCheckSanity(Key, params)
	ReportStatus('running stat')
	CommandResp(Key, 'ok', params, None)


def LogItem(sev, params=None, Key=None):
	TempCheckSanity(Key, params)
	logsupport.Logs.Log('Remotely forced test message ({})'.format(sev), severity=sev, tb=False, hb=False)
	CommandResp(Key, 'ok', params, None)


def GetErrors(params=None):  # remote only
	errs = logsupport.Logs.ReturnRecent(logsupport.ConsoleWarning, 10)
	CommandResp(None, 'ok', params, errs)


def GetLog(params=None):  # remote only
	log = logsupport.Logs.ReturnRecent(-1, 0)
	CommandResp(None, 'ok', params, log)


def ClearIndicator(params=None, Key=None):
	TempCheckSanity(Key, params)
	config.sysStore.ErrorNotice = -1  # clear indicator
	ReportStatus('cleared indicator')
	CommandResp(Key, 'ok', params, None)


def GetVar(params=None, Key=None):
	print(params, Key)
	if len(params) < 4:
		logsupport.Logs.Log('No request to remote GetVar command {}'.format(params), severity=ConsoleWarning)
		return
	try:
		p = json.loads(params[3])
		assert (type(p) == dict)
	except Exception as E:
		logsupport.Logs.Log(f'Non-dict paramater to remote GetVar command: {params} ({E}', severity=ConsoleWarning)
		return
	resp = {}
	for v, val in p.items():
		try:
			val = valuestore.GetVal(v)
			logsupport.Logs.Log('Remote get of {} to {}'.format(v, val))
			resp[v] = val
		except Exception as E:
			logsupport.Logs.Log(f'Bad store attempt in remote SetVar command: {v}={val} ({E}',
								severity=ConsoleWarning)
	CommandResp(Key, 'ok', params, resp)


def SetVar(params=None):
	print(params)
	if len(params) < 4:
		logsupport.Logs.Log('No request to remote SetVar command {}'.format(params), severity=ConsoleWarning)
		return
	try:
		p = json.loads(params[3])
		assert (type(p) == dict)
	except Exception as E:
		logsupport.Logs.Log(f'Non-dict paramater to remote SetVar command: {params} ({E})', severity=ConsoleWarning)
		raise
	for v, val in p.items():
		try:
			valuestore.SetVal(v, val)
			logsupport.Logs.Log('Remote set of {} to {}'.format(v, val))
		except Exception as E:
			logsupport.Logs.Log(f'Bad store attempt in remote SetVar command: {v}={val} ({E})',
								severity=ConsoleWarning)


def SendErrMatch(params=None, Key=None):
	TempCheckSanity(Key, params)
	try:
		lev, msg = literal_eval(params[3])
	except (SyntaxError, ValueError, TypeError, MemoryError):
		logsupport.Logs.Log('Bad last error received in clear match cmd: {}'.format(params))
		CommandResp(Key, 'nomatch', params, None)
		return
	if logsupport.Logs.MatchLastErr(lev, msg, logsupport.ConsoleWarning):
		config.sysStore.ErrorNotice = -1  # clear indicator
		ReportStatus('cleared indicator')
		CommandResp(Key, 'ok', params, None)
	else:
		CommandResp(Key, 'nomatch', params, None)


def IncludeErrToMatch():
	return lastseenlogmessage


def DelHistory(params=None, Key=None):
	logsupport.Logs.Log('Got request from {} to delete history for {}'.format(params[2], params[3]))
	DeleteNode(params[3])
	CommandResp(Key, 'ok', params, None)


Where = Enum('Where',
			 'LocalMenuExits LocalMenuVersions LocalMenuVersionsAdv RemoteMenu RemoteMenuAdv MQTTCmds RemoteMenuDead')
MaintVers = (Where.LocalMenuVersions, Where.RemoteMenu, Where.MQTTCmds)
MaintVersAdv = (Where.LocalMenuVersionsAdv, Where.RemoteMenuAdv, Where.MQTTCmds)
MaintExits = (Where.LocalMenuExits, Where.RemoteMenu, Where.MQTTCmds)
RemoteOnly = (Where.RemoteMenu, Where.MQTTCmds)
RemoteOnlyAdv = (Where.RemoteMenuAdv, Where.MQTTCmds)
RemoteOnlyDead = (Where.RemoteMenuDead,)
MQTTOnly = (Where.MQTTCmds,)

'''
CommandRecord = NamedTuple('CommandRecord',
						   [('Proc', Callable), ('simple', bool), ('DisplayName', str), ('Verify', str),
							('where', tuple), ('notgroup', bool), ('cmdparam', Callable)])
CommandRecord.__new__.__defaults__ = (None)
'''


# Better Python 3.7 syntax
@dataclass
class CommandRecord:
	Proc: callable  # called locally or at remote site
	simple: bool  # simple or None - handle remote response simply or call a special proc (name mapping in consolestatus
	DisplayName: str  # button label when on a screen
	Verify: str  # whether to do verify when on a screen
	where: tuple  # which places to use this record
	notgroup: bool  # true if only works for targeted node
	suppresstoself: bool  # true if suppress "all" on sending node
	cmdparam: Union[Callable, None] = None  # - optional proc that provides a parameter to send with the command


cmdcalls = OrderedDict({
	'restart': CommandRecord(RestartConsole, True, "Restart Console", 'True', MaintExits, False, True),
	'shut': CommandRecord(ShutConsole, True, "Shutdown Console", 'True', MaintExits, False, True),
	'reboot': CommandRecord(RebootPi, True, "Reboot Pi", 'True', MaintExits, False, True),
	'shutpi': CommandRecord(ShutdownPi, True, "Shutdown Pi", 'True', MaintExits, False, True),
	'usestable': CommandRecord(UseStable, True, "Use Stable Release", 'False', MaintVers, False, True),
	'usebeta': CommandRecord(UseBeta, True, "Use Beta Release", 'False', MaintVers, False, True),
	'usedev': CommandRecord(UseDev, True, "Use Development Release", 'False', MaintVersAdv, False, True),
	'freezeconfig': CommandRecord(FreezeConfig, True, 'Freeze Configuration', 'False', MaintVersAdv, False, True),
	'unfreezeconfig': CommandRecord(UnfreezeConfig, True, 'Unfreeze Configuration', 'False', MaintVersAdv, False, True),
	'getstable': CommandRecord(GetStable, True, "Download Release", 'False', MaintVers, False, True),
	'getbeta': CommandRecord(GetBeta, True, "Download Beta", 'False', MaintVers, False, True),
	'getdev': CommandRecord(GetDev, True, "Download Development", 'False', MaintVersAdv, False, True),
	'hbdump': CommandRecord(DumpHB, True, "Dump HB", 'False', RemoteOnlyAdv, False, False),
	# 'status': CommandRecord(EchoStat, True, "Echo Status", 'False', RemoteOnly),
	'getlog': CommandRecord(GetLog, False, "Get Remote Log", "False", RemoteOnly, True, True),
	'geterrors': CommandRecord(GetErrors, False, "Get Recent Errors", 'False', RemoteOnly, True, True),
	'clearerrindicator': CommandRecord(ClearIndicator, True, "Clear Error Indicator", 'False', RemoteOnly, False,
									   False),
	'clearerrindicatormatch': CommandRecord(SendErrMatch, True, 'Clear Matching Error', 'False', RemoteOnly, False,
											False,
											IncludeErrToMatch),
	'issueerror': CommandRecord(functools.partial(LogItem, ConsoleError), True, "Issue Error", 'False',
								RemoteOnlyAdv, False, True),
	'issuewarning': CommandRecord(functools.partial(LogItem, ConsoleWarning), True, "Issue Warning", 'False',
								  RemoteOnlyAdv, False, True),
	'issueinfo': CommandRecord(functools.partial(LogItem, ConsoleInfo), True, "Issue Info", 'False',
							   RemoteOnlyAdv, False, True),
	'deletehistory': CommandRecord(DelHistory, True, 'Clear History', 'True', RemoteOnlyDead, True, True),
	'setvar': CommandRecord(SetVar, True, "Set Variable Value", 'False', MQTTOnly, False, True),
	'getvar': CommandRecord(GetVar, False, "Get Variable Value", 'False', MQTTOnly, True, True)})


def IssueCommand(source, cmd, seq, fromnd, param=None):
	if cmd.lower() in cmdcalls:
		if fromnd == hw.hostname and cmdcalls[cmd.lower()].suppresstoself:
			logsupport.Logs.Log(
				'Ignore remote command {} to ALL from self'.format(cmd))
			return
		try:
			PostEvent(
				ConsoleEvent(CEvent.RunProc, name=cmd, proc=cmdcalls[cmd.lower()].Proc,
							 params=(cmd, seq, fromnd, param)))
		except Exception as E:
			logsupport.Logs.Log('Exc: {}'.format(repr(E)))
	else:
		logsupport.Logs.Log('{}: Unknown remote command request: {}'.format(source, cmd),
							severity=ConsoleWarning)


def fetch_stable():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt stable", hold=1)
	# noinspection PyBroadException
	try:
		if os.path.exists(basedir + '/homesystem'):
			# personal system
			logsupport.Logs.Log("New version fetch(homerelease)")
			logsupport.DevPrint("New Version Fetch Requested (homesystem)")
			U.StageVersion(basedir + '/consolestable', 'homerelease', 'Maint Dnld', logger=logsupport.Logs)
		else:
			logsupport.Logs.Log("New version fetch(currentrelease)")
			logsupport.DevPrint("New Version Fetch Requested (currentrelease)")
			U.StageVersion(basedir + '/consolestable', 'currentrelease', 'Maint Dnld', logger=logsupport.Logs)
		U.InstallStagedVersion(basedir + '/consolestable', logger=logsupport.Logs)
		logsupport.Logs.Log("Staged version installed in consolestable")
	except Exception as E:
		logsupport.Logs.Log(f'Failed release download ({E})', severity=ConsoleWarning)
	ReportStatus("done stable", hold=2)


def fetch_beta():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt beta", hold=1)
	logsupport.Logs.Log("New version fetch(currentbeta)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'Maint Dnld', logger=logsupport.Logs)
		U.InstallStagedVersion(basedir + '/consolebeta', logger=logsupport.Logs)
		logsupport.Logs.Log("Staged version installed in consolebeta")
	except Exception as E:
		logsupport.Logs.Log(f'Failed beta download ({E})', severity=ConsoleWarning)
	ReportStatus("done beta", hold=2)


def fetch_dev():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt dev", hold=1)
	logsupport.Logs.Log("New version fetch(currentdev)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consoledev', '*live*', 'Maint Dnld', logger=logsupport.Logs)
		U.InstallStagedVersion(basedir + '/consoledev', logger=logsupport.Logs)
		logsupport.Logs.Log("Staged version installed in consoledev")
	except Exception as E:
		logsupport.Logs.Log(f'Failed dev download ({E})', severity=ConsoleWarning)
	ReportStatus("done dev", hold=2)
