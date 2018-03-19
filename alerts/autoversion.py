import config
import githubutil
import exitutils
import sys
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail
import alerttasks

class AutoVersion(object):
	def __init__(self):
		pass

	# @staticmethod
	def CheckUpToDate(self, alert):
		exiting = False
		if config.versionname not in ('none', 'development'):  # skip if we don't know what is running
			config.DS.Tasks.StartLongOp()  # todo perhaps a cleaner way to deal with long ops
			logsupport.Logs.Log("Autoversion found named version running: ",config.versionname, severity=ConsoleDetail)
			try:  # if network is down or other error occurs just skip for now rather than blow up
				sha, c = githubutil.GetSHA(config.versionname)
				#logsupport.Logs.Log('sha: ',sha, ' cvshha: ',config.versionsha,severity=ConsoleDetail)
				if sha <> config.versionsha and sha <> 'no current sha':
					logsupport.Logs.Log('Current hub version different')
					logsupport.Logs.Log(
						'Running (' + config.versionname + '): ' + config.versionsha + ' of ' + config.versioncommit)
					logsupport.Logs.Log('Getting: ' + sha + ' of ' + c)
					githubutil.StageVersion(config.exdir, config.versionname, 'Automatic download')
					githubutil.InstallStagedVersion(config.exdir)
					logsupport.Logs.Log("Staged version installed in ", config.exdir)
					exiting = True
					logsupport.Logs.Log('Restart for new version')
					exitutils.Exit(exitutils.AUTORESTART)
				elif sha == 'no current sha':
					logsupport.Logs.Log('No sha for autoversion: ',config.versionname,severity=ConsoleWarning)
				else:
					pass
					#logsupport.Logs.Log('sha equal ',sha,severity=ConsoleDetail)

			except:
				if not exiting:
					logsupport.Logs.Log(
						'Github check not available' + str(sys.exc_info()[0]) + ': ' + str(sys.exc_info()[1]),
						severity=ConsoleWarning)
			config.DS.Tasks.EndLongOp()
		else:
			logsupport.Logs.Log("Auto version found special version running: ",config.versionname)


alerttasks.alertprocs["AutoVersion"] = AutoVersion
