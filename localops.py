import os
import shutil
import config
import logsupport

NewCfgs = set()
DeletedCfgs = set()
CopiedConfig = ''
PreOpFailure = []


def PreOp():
	global DeletedCfgs, CopiedConfig, NewCfgs, PreOpFailure
	if not os.path.exists(config.sysStore.HomeDir + '/homesystem'):
		return

	confserver = '/home/pi/.exconfs/'
	conflocal = config.sysStore.configdir + '/cfglib/'
	cfgdirserver = confserver + 'cfglib/'
	newerlocal = config.sysStore.configdir + '/newer/'
	try:
		os.mkdir(newerlocal)
	except Exception:
		pass

	try:
		cfgliblocal = set([f for f in os.listdir(conflocal) if os.path.isfile(os.path.join(conflocal, f))])
		cfglibserver = set([f for f in os.listdir(cfgdirserver) if os.path.isfile(os.path.join(cfgdirserver, f))])
	except Exception as E:
		PreOpFailure.append("Getting cfglists ({})".format(E))
		cfgliblocal = set()
		cfglibserver = set()

	try:
		for f in cfglibserver:
			mt = os.path.getmtime(cfgdirserver + f)
			try:
				mtloc = os.path.getmtime(conflocal + f)
			except:
				mtloc = 0
			if mt > mtloc:
				NewCfgs.add(f)
				shutil.copy2(cfgdirserver + f, conflocal + f)
			elif mt < mtloc:
				shutil.copy2(conflocal + f, newerlocal)
				shutil.copy2(cfgdirserver + f, conflocal + f)
				PreOpFailure.append('Newer cfglib file on local system: {}'.format(f))
		DeletedCfgs = cfgliblocal - cfglibserver
	except Exception as E:
		PreOpFailure.append("Copying cfglib files ({})".format(E))
		DeletedCfgs = set()

	try:
		cfgfilesrv = confserver + 'config-' + config.sysStore.hostname + '.txt'
		cfgfileloc = config.sysStore.configdir + '/config-' + config.sysStore.hostname + '.txt'
		mt = os.path.getmtime(cfgfilesrv)
		mtloc = os.path.getmtime(cfgfileloc)
		if mt > mtloc:
			shutil.copy2(cfgfilesrv, cfgfileloc)
			CopiedConfig = cfgfileloc
		elif mt < mtloc:
			shutil.copy2(cfgfileloc, newerlocal)
			shutil.copy2(cfgfilesrv, cfgfileloc)
			PreOpFailure.append('Newer main config file on local system')
	except Exception as E:
		PreOpFailure.append("Copying main config file ({})".format(E))


def LogUp():
	global NewCfgs, DeletedCfgs, PreOpFailure, CopiedConfig
	logsupport.Logs.Log('-----Local Ops Executed-----')
	for f in NewCfgs:
		logsupport.Logs.Log("Updated cfg library element: {}".format(f))
	if CopiedConfig != "":
		logsupport.Logs.Log("Updated host config file: {}".format(CopiedConfig))
	for f in DeletedCfgs:
		logsupport.Logs.Log("Local config library file {} no longer exists in archive".format(f))
	for l in PreOpFailure:
		logsupport.Logs.Log('PreOp Error: {}'.format(l), severity=logsupport.ConsoleWarning)
	logsupport.Logs.Log('-----Local Ops Complete-----')
