import config
import githubutil
import exitutils
import sys
from logsupport import ConsoleWarning

class AutoVersion(object):
	def __init__(self):
		pass

	# @staticmethod
	def CheckUpToDate(self, alert):
		exiting = False
		if config.versionname not in ('none', 'development'):  # skip if we don't know what is running
			config.DS.Tasks.StartLongOp()  # todo perhaps a cleaner way to deal with long ops
			try:  # if network is down or other error occurs just skip for now rather than blow up
				sha, c = githubutil.GetSHA(config.versionname)
				if sha <> config.versionsha:
					config.Logs.Log('Current hub version different')
					config.Logs.Log(
						'Running (' + config.versionname + '): ' + config.versionsha + ' of ' + config.versioncommit)
					config.Logs.Log('Getting: ' + sha + ' of ' + c)
					githubutil.StageVersion(config.exdir, config.versionname, 'Automatic download')
					githubutil.InstallStagedVersion(config.exdir)
					config.Logs.Log("Staged version installed in ", config.exdir)
					exiting = True
					config.Logs.Log('Restart for new version')
					exitutils.Exit(exitutils.AUTORESTART)
			except:
				if not exiting:
					config.Logs.Log(
						'Github check not available' + str(sys.exc_info()[0]) + ': ' + str(sys.exc_info()[1]),
						severity=ConsoleWarning)
			config.DS.Tasks.EndLongOp()


config.alertprocs["AutoVersion"] = AutoVersion
