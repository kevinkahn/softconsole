import config
import githubutil
import exitutils
import eventlist


class AutoVersion(object):
	def __init__(self):
		pass

	def CheckUpToDate(self, alert):
		print 'Check'
		if config.versionname not in ('none', 'development'):  # skip if we don't know what is running
			config.DS.Tasks.StartLongOp()  # todo perhaps a cleaner way to deal with long ops
			sha, c = githubutil.GetSHA(config.versionname)
			if sha <> config.versionsha:
				config.Logs.Log('Current hub version different')
				config.Logs.Log(
					'Running (' + config.versionname + '): ' + config.versionsha + ' of ' + config.versioncommit)
				config.Logs.Log('Getting: ' + sha + ' of ' + c)
				githubutil.StageVersion(config.exdir, config.versionname, 'Automatic download')
				githubutil.InstallStagedVersion(config.exdir)
				config.Logs.Log('Restart for new version')
				exitutils.Exit('restart', 'auto', 0)
			# print 'Suppressed auto restart'
			config.DS.Tasks.EndLongOp()


config.alertprocs["AutoVersion"] = AutoVersion
