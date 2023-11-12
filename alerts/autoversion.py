import sys, os

from alertsystem import alerttasks, alertutils
import config
import githubutil
import historybuffer
import logsupport
import threading
from logsupport import ConsoleWarning, ConsoleDetail
from consolestatus import ReportStatus

def DoFetchRestart():
	global fetcher
	try:
		historybuffer.HBNet.Entry('Autoversion get sha')
		sha, c = githubutil.GetSHA(config.sysStore.versionname)
		historybuffer.HBNet.Entry('Autoversion get sha done')
		# logsupport.Logs.Log('sha: ',sha, ' cvshha: ',config.versionsha,severity=ConsoleDetail)
		if sha != config.sysStore.versionsha and sha != 'no current sha' and not os.path.isfile(
				'../.freezeconfig'):  # check frozen todo
			logsupport.Logs.Log('Current hub version different')
			logsupport.Logs.Log(
				'Running (' + config.sysStore.versionname + '): ' + config.sysStore.versionsha + ' of ' + config.sysStore.versioncommit)
			logsupport.Logs.Log('Getting: ' + sha + ' of ' + c)
		elif sha == 'no current sha':
			logsupport.Logs.Log('No sha for autoversion: ', config.sysStore.versionname, severity=ConsoleWarning)
			fetcher = None  # allow next autoversion to proceed
			return
		elif os.path.exists("../.freezeconfig"):
			logsupport.Logs.Log('Configuration files frozen')
			fetcher = None
			return
		else:
			fetcher = None  # allow next autoversion to proceed
			return
	except Exception as E:
		historybuffer.HBNet.Entry('GitHub access failure: {}:{}'.format(str(sys.exc_info()[0]), str(sys.exc_info()[1])))
		logsupport.Logs.Log('Github check not available ({})'.format(E), severity=ConsoleWarning)
		fetcher = None  # allow next autoversion to proceed
		return
	try:
		logsupport.Logs.Log('Update fetch started')
		ReportStatus("auto updt firmware", hold=1)
		githubutil.StageVersion(config.sysStore.ExecDir, config.sysStore.versionname, 'Auto Dnld')
		logsupport.Logs.Log('Update fetch thread staged')
		ReportStatus("auto install firmware", hold=1)
		githubutil.InstallStagedVersion(config.sysStore.ExecDir)
		logsupport.Logs.Log("Staged version installed in ", config.sysStore.ExecDir)
		logsupport.Logs.Log('Restart for new version')
		alertutils.UpdateRestartStatus('Autoversion Restart Event', 'autoversion')
		fetcher = None
	except Exception as E:
		historybuffer.HBNet.Entry(
			'Version access failure: {}:{}'.format(str(sys.exc_info()[0]), str(sys.exc_info()[1])))
		logsupport.Logs.Log('Version access failed ({})'.format(E), severity=ConsoleWarning)
		fetcher = None  # allow next autoversion to proceed

fetcher = None

# noinspection PyUnusedLocal
class AutoVersion(object):
	def __init__(self):
		global fetcher
		fetcher = None

	# @staticmethod
	@staticmethod
	def CheckUpToDate(alert):
		global fetcher
		if config.sysStore.versionname not in ('none', 'development'):  # skip if we don't know what is running
			logsupport.Logs.Log("Autoversion found named version running: ", config.sysStore.versionname, severity=ConsoleDetail)
			if fetcher is not None and not fetcher.is_alive():
				logsupport.Logs.Log('Autoversion fetcher found unexpectedly dead - retrying', severity=ConsoleWarning)
				fetcher = None
			# noinspection PyBroadException
			if fetcher is None:
				fetcher = threading.Thread(name='AutoVersionFetch', target=DoFetchRestart, daemon=True)
				fetcher.start()
			else:
				logsupport.Logs.Log('Autoversion fetch while previous fetch still in progress')
		else:
			logsupport.Logs.Log("Auto version found special version running: ", config.sysStore.versionname)


alerttasks.alertprocs["AutoVersion"] = AutoVersion
