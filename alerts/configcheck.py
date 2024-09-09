from alertsystem import alerttasks
import config
from config import configfilelist
from alertsystem.alertutils import UpdateRestartStatus
import os, datetime
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail
from utils.utilfuncs import safeprint

confserver = '/home/pi/.exconfs/'
cfgdirserver = confserver + 'cfglib/'
reporteddifferences = {}
reftime = os.path.getmtime('console.py')  # use as install time of the console tar
reftimes = datetime.datetime.fromtimestamp(reftime).strftime('%Y-%m-%d %H:%M:%S')


def ConfigFilesChanged():
	changes = False
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
			if ftime == reftime:
				# local file was part of an initial install
				reporteddifferences[fb] = mts
				logsupport.Logs.Log(
					'Local config file {} part of initial install stamped {} (Ref time {})'.format(fb, ftimes,
																								   reftimes))  # todo make this a ConsoleDetail message
			elif fb not in reporteddifferences or reporteddifferences[fb] != mts:
				reporteddifferences[fb] = mts
				logsupport.Logs.Log(
					'Local config file {} {} newer than master: {}'.format(fb, ftimes, mts), severity=ConsoleWarning)
		else:
			pass

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
