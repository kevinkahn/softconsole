import os
import threading
import subprocess
import functools
import json

import githubutil as U
import logsupport
import historybuffer
import time
from logsupport import ConsoleWarning, ConsoleError, ConsoleInfo, ReportStatus
from controlevents import PostEvent, ConsoleEvent, CEvent
import timers
import config
from collections import OrderedDict
from typing import NamedTuple, Callable
from enum import Enum
from exitutils import MAINTEXIT, Exit_Screen_Message, MAINTRESTART, MAINTPISHUT, MAINTPIREBOOT, Exit, REMOTERESTART, \
	REMOTEEXIT, REMOTEPISHUT, REMOTEPIREBOOT

fetcher = None


def oldFetchInProgress(reason, action, Key=None):
	global fetcher
	print('Call fetch {}'.format(repr(Key)))
	if fetcher is not None and fetcher.is_alive():
		if Key is None:
			print('sched shut')
			# remote or AutoVer restart
			logsupport.Logs.Log('Delaying {} until fetch completes'.format(reason))
			dly = timers.OnceTimer(10, start=True, name='FetchDelay', proc=DoDelayedAction, action=action)
			ReportStatus('wait restart', hold=1)
		else:
			print('just flash')
			Key.FlashNo(5)
		return True
	else:
		return False


def TempCheckSanity(Key, params):  # tempdel
	if Key is None and params is None:
		logsupport.Logs.Log('Internal Error: Both Command sources are None', severity=ConsoleError, tb=True, hb=True)


def FetchInProgress():
	global fetcher
	return fetcher is not None and fetcher.is_alive()

# todo further compress below to unify messagint
def RestartConsole(params=None, Key=None, AutoVer=False):  # todo sort out autovers
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
	Exit_Screen_Message(exitmsg + ' Requested', ('Remote' if Key is None else 'Maintenance') + ' Request', exitmsg)
	config.terminationreason = ('remote' if Key is None else 'manual') + statmsg
	CommandResp(Key, 'ok', params, None)
	Exit(exitcode[1] if Key is None else exitcode[0])


def DoDelayedAction(evnt):  # only for autover todo - what about ISY cmds - deprecate
	PostEvent(ConsoleEvent(CEvent.RunProc, name='DelayedRestart', proc=evnt.action))


def CommandResp(Key, success, params, value):
	print('CR: {} {}'.format(params, value))
	if Key is not None:
		if success == 'ok':
			Key.ScheduleBlinkKey(5)
		else:
			Key.FlashNo(5)
	else:
		config.MQTTBroker.CommandResponse(success, params[0], params[1], params[2], value)


def Get(nm, target, params, Key):
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
	subprocess.Popen('sudo echo stable > /home/pi/versionselector', shell=True)
	CommandResp(Key, 'ok', params, None)


def UseBeta(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('sudo echo beta > /home/pi/versionselector', shell=True)
	CommandResp(Key, 'ok', params, None)


def UseDev(params=None, Key=None):
	TempCheckSanity(Key, params)
	subprocess.Popen('sudo echo dev > /home/pi/versionselector', shell=True)
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
	print('Log {}'.format(params))
	logsupport.Logs.Log('Remotely forced test message ({})'.format(sev), severity=sev, tb=False, hb=False)
	CommandResp(Key, 'ok', params, None)


def GetErrors(params=None):  # remote only
	errs = logsupport.Logs.ReturnRecent(logsupport.ConsoleDetail, 10)
	CommandResp(None, 'ok', params, errs)


def GetLog(params=None):  # remote only
	log = logsupport.Logs.ReturnRecemt(-1, 0)
	CommandResp(None, 'ok', params, None)


def DisplayRemoteLog():
	pass

Where = Enum('Where',
			 'LocalMenuExits LocalMenuVersions RemoteMenu MQTTCmds')
MaintVers = (Where.LocalMenuVersions, Where.RemoteMenu, Where.MQTTCmds)
MaintExits = (Where.LocalMenuExits, Where.RemoteMenu, Where.MQTTCmds)

CommandRecord = NamedTuple('CommandRecord',
						   [('Proc', Callable), ('simple', bool), ('DisplayName', str), ('Verify', str),
							('where', tuple)])
'''
Better Python 3.7 syntax
class CommandRecord(NamedTuple):
	def __init__(self,Proc,simple,DisplayName,Verify,where):
		self.Proc = Proc  - called locally or at remote site
		self.simple = simple or None - handle remote response simply or call a special proc (name mapping in consolestatus
		self.DisplayName = DisplayName - button label when on a screen
		self.Verify = Verify - whether to do a verify when on a screen
		self.where = where - which places to use this record
'''
cmdcalls = OrderedDict({
	'restart': CommandRecord(RestartConsole, True, "Restart Console", 'True', MaintExits),
	'shut': CommandRecord(ShutConsole, True, "Shutdown Console", 'True', MaintExits),
	'reboot': CommandRecord(RebootPi, True, "Reboot Pi", 'True', MaintExits),
	'shutpi': CommandRecord(ShutdownPi, True, "Shutdown Pi", 'True', MaintExits),
	'usestable': CommandRecord(UseStable, True, "Use Stable Release", 'False', MaintVers),
	'usebeta': CommandRecord(UseBeta, True, "Use Beta Release", 'False', MaintVers),
	'usedev': CommandRecord(UseDev, True, "Use Development Release", 'False', MaintVers),
	'getstable': CommandRecord(GetStable, True, "Download Release", 'False', MaintVers),
	'getbeta': CommandRecord(GetBeta, True, "Download Beta", 'False', MaintVers),
	'getdev': CommandRecord(GetDev, True, "Download Development", 'False', MaintVers),
	'hbdump': CommandRecord(DumpHB, True, "Dump HB", 'False', (Where.RemoteMenu, Where.MQTTCmds)),
	'status': CommandRecord(EchoStat, True, "Echo Status", 'False', (Where.MQTTCmds,)),
	'getlog': CommandRecord(GetLog, False, "Get Remote Log", "False", (Where.MQTTCmds, Where.RemoteMenu)),
	'geterrors': CommandRecord(GetErrors, False, "Get Recent Errors", 'False', (Where.MQTTCmds, Where.RemoteMenu)),
	'issueerror': CommandRecord(functools.partial(LogItem, ConsoleError), True, "Issue Error", 'False',
								(Where.RemoteMenu, Where.MQTTCmds)),
	'issuewarning': CommandRecord(functools.partial(LogItem, ConsoleWarning), True, "Issue Warning", 'False',
								  (Where.RemoteMenu, Where.MQTTCmds)),
	'issueinfo': CommandRecord(functools.partial(LogItem, ConsoleInfo), True, "Issue Info", 'False',
							   (Where.RemoteMenu, Where.MQTTCmds))})


def IssueCommand(source, cmd, seq, fromnd):
	if cmd.lower() in cmdcalls:
		try:
			PostEvent(
				ConsoleEvent(CEvent.RunProc, name=cmd, proc=cmdcalls[cmd.lower()].Proc, params=(cmd, seq, fromnd)))
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
			U.StageVersion(basedir + '/consolestable', 'homerelease', 'Maint Dnld')
		else:
			logsupport.Logs.Log("New version fetch(currentrelease)")
			logsupport.DevPrint("New Version Fetch Requested (currentrelease)")
			U.StageVersion(basedir + '/consolestable', 'currentrelease', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consolestable')
		logsupport.Logs.Log("Staged version installed in consolestable")
	except:
		logsupport.Logs.Log('Failed release download', severity=ConsoleWarning)
	ReportStatus("done stable", hold=2)


def fetch_beta():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt beta", hold=1)
	logsupport.Logs.Log("New version fetch(currentbeta)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consolebeta')
		logsupport.Logs.Log("Staged version installed in consolebeta")
	except:
		logsupport.Logs.Log('Failed beta download', severity=ConsoleWarning)
	ReportStatus("done beta", hold=2)


def fetch_dev():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt dev", hold=1)
	logsupport.Logs.Log("New version fetch(currentdev)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consoledev', '*live*', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consoledev')
		logsupport.Logs.Log("Staged version installed in consoledev")
	except:
		logsupport.Logs.Log('Failed dev download', severity=ConsoleWarning)
	ReportStatus("done dev", hold=2)
