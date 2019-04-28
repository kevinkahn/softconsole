import sys

import alerttasks
import config
import exitutils
import githubutil
import logsupport
import timers
import threading
from logsupport import ConsoleWarning, ConsoleDetail, ReportStatus
import controlevents


def DoFetchRestart():
	logsupport.Logs.Log('Update fetch thread started')
	ReportStatus("auto updt firmware", hold = 1)
	githubutil.StageVersion(config.sysStore.ExecDir, config.sysStore.versionname, 'Auto Dnld')
	logsupport.Logs.Log('Update fetch thread staged')
	ReportStatus("auto install firmware", hold = 1)
	githubutil.InstallStagedVersion(config.sysStore.ExecDir)
	logsupport.Logs.Log("Staged version installed in ", config.sysStore.ExecDir)
	logsupport.Logs.Log('Restart for new version')
	ReportStatus('auto restart', hold = 2)
	controlevents.PostEvent(controlevents.ConsoleEvent(controlevents.CEvent.RunProc,proc=ForceRestart, name=ForceRestart))
	#exitutils.Exit(exitutils.AUTORESTART)

def ForceRestart():
	logsupport.Logs.Log('Autoversion Restart Event')
	config.terminationreason = 'autoversion'
	exitutils.Exit(exitutils.AUTORESTART)

fetcher = None

# noinspection PyUnusedLocal
class AutoVersion(object):
	def __init__(self):
		fetchrestartinprogress = False
		fetcher = None

	# @staticmethod
	@staticmethod
	def CheckUpToDate(alert):
		global fetcher
		if config.sysStore.versionname not in ('none', 'development'):  # skip if we don't know what is running
			timers.StartLongOp('AutoVersion')
			logsupport.Logs.Log("Autoversion found named version running: ", config.sysStore.versionname, severity=ConsoleDetail)
			# noinspection PyBroadException
			try:  # if network is down or other error occurs just skip for now rather than blow up
				sha, c = githubutil.GetSHA(config.sysStore.versionname)
				# logsupport.Logs.Log('sha: ',sha, ' cvshha: ',config.versionsha,severity=ConsoleDetail)
				if sha != config.sysStore.versionsha and sha != 'no current sha':
					logsupport.Logs.Log('Current hub version different')
					logsupport.Logs.Log(
						'Running (' + config.sysStore.versionname + '): ' + config.sysStore.versionsha + ' of ' + config.sysStore.versioncommit)
					logsupport.Logs.Log('Getting: ' + sha + ' of ' + c)
					if fetcher is None:
						fetcher = threading.Thread(name='AutoVersionFetch', target=DoFetchRestart, daemon=True)
						fetcher.start()
					else:
						logsupport.Logs.Log('Autoversion fetch while previous fetch still in progress')
				elif sha == 'no current sha':
					logsupport.Logs.Log('No sha for autoversion: ', config.sysStore.versionname, severity=ConsoleWarning)
				else:
					pass
			# logsupport.Logs.Log('sha equal ',sha,severity=ConsoleDetail)

			except:
				logsupport.Logs.Log(
						'Github check not available' + str(sys.exc_info()[0]) + ': ' + str(sys.exc_info()[1]),
						severity=ConsoleWarning)
			timers.EndLongOp('AutoVersion')
		else:
			logsupport.Logs.Log("Auto version found special version running: ", config.sysStore.versionname)


alerttasks.alertprocs["AutoVersion"] = AutoVersion
