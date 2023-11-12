from alertsystem import alerttasks
import config
from config import configfilelist
from alertutils import UpdateRestartStatus
import os, datetime
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail
from utils.utilfuncs import safeprint

confserver = '/home/pi/.exconfs/'
cfgdirserver = confserver + 'cfglib/'
reporteddifferences = {}

def ConfigFilesChanged():
	changes = False
	# safeprint('CheckConfig')
	with open('/home/pi/Console/configcheck', 'w') as lgf:
		safeprint('Config File Check', file=lgf)
	for f, ftime in configfilelist.items():
		ftimes = datetime.datetime.fromtimestamp(ftime).strftime('%Y-%m-%d %H:%M:%S')
		fl, fb = f.split('/')[-2:]
		if fl == 'cfglib':
			try:
				mt = os.path.getmtime(cfgdirserver + fb)
				mts = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')
			except Exception as E:
				mt = ftime
				mts = 'None'
				safeprint('Error getting current library timestamp {}'.format(E))
		elif fl == 'local':
			mt = ftime
			mts = 'skip'
		else:
			try:
				mt = os.path.getmtime(confserver + fb)
				mts = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')
			except Exception as E:
				mt = ftime
				mts = 'None'
				safeprint('Error getting current base timestamp {}'.format(E))
		if mt - ftime > 0:  # newer file in master directory
			changes = True
			logsupport.Logs.Log(
				'Configuration file change: file: {} was: {} now: {} diff: {}'.format(fb, ftimes, mts, mt - ftime))
			with open('/home/pi/Console/configcheck', 'a') as lgf:
				safeprint('***************************', file=lgf)
				safeprint('{} changed (was: {} now: {} diff: {}'.format(fb, ftimes, mts, ftime - mt), file=lgf)
				safeprint('***************************', file=lgf)
		elif ftime - mt > 0:  # newer file locally - report that
			if fb not in reporteddifferences or reporteddifferences[fb] != mts:
				reporteddifferences[fb] = mts
				logsupport.Logs.Log(
					'Local config file {} {} newer than master: {}'.format(fb, ftimes, mts), severity=ConsoleWarning)
		else:
			pass
	# with open('/home/pi/Console/configcheck', 'a') as lgf:
	#	safeprint('{} ok {} vs {} diff: {}'.format(f, ftimes, mts, ftime-mt), file=lgf)

	safeprint('Changes = {}'.format(changes))
	return changes


class ConfigCheck(object):

	# noinspection PyUnusedLocal
	@staticmethod
	def ConfigCheck(alert):
		if config.sysStore.versionname in ('none', 'development'):  # skip if we don't know what is running
			logsupport.Logs.Log("ConfigCheck found non-deployment version running: ", config.sysStore.versionname,
								severity=ConsoleDetail)
		elif ConfigFilesChanged():
			if os.path.exists("../.freezeconfig"):
				logsupport.Logs.Log('Config check found changes while configs frozen')
				return
			else:
				logsupport.Logs.Log('Restart config update')
				UpdateRestartStatus('Configuration Update Needed', 'configcheck')



alerttasks.alertprocs["ConfigCheck"] = ConfigCheck
