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
		print('Not home system')
		return

	confserver = '/home/pi/.exconf/'
	conflocal = config.sysStore.configdir + '/cfglib/'
	cfgdirserver = confserver + 'cfglib/'

	try:
		cfgliblocal = set(os.listdir(conflocal))
		cfglibserver = set(os.listdir(cfgdirserver))
	except Exception as E:
		PreOpFailure.append("Getting cfglists ({})".format(E))
		cfgliblocal = set()
		cfglibserver = set()

	try:
		for f in cfglibserver:
			mt = os.path.getmtime(cfgdirserver + f)
			mtloc = os.path.getmtime(conflocal + f)
			if mt != mtloc:
				NewCfgs.add(f)
				shutil.copyfile(cfgdirserver + f, conflocal + f)
			DeletedCfgs = cfgliblocal - cfglibserver
	except Exception as E:
		PreOpFailure.append("Copying cfglib files ({})".format(E))
		DeletedCfgs = set()

	try:
		cfgfilesrv = confserver + 'config-' + config.sysStore.hostname + '.txt'
		cfgfileloc = config.sysStore.configdir + 'config-' + config.sysStore.hostname + '.txt'
		mt = os.path.getmtime(cfgfilesrv)
		mtloc = os.path.getmtime(cfgfileloc)
		if mt > mtloc:
			shutil.copyfile(cfgfilesrv, cfgfileloc)
			CopiedConfig = cfgfileloc
		elif mt < mtloc:
			PreOpFailure.append('Newer main config file on local system')
	except Exception as E:
		PreOpFailure.append("Copying main config file ({})".format(E))


def LogUp():
	global NewCfgs, DeletedCfgs, PreOpFailure, CopiedConfig
	for f in NewCfgs:
		logsupport.Logs.Log("Updated cfg library element: {}".format(f))
	if CopiedConfig != "":
		logsupport.Logs.Log("Updated host config file: {}".format(CopiedConfig))
	for f in DeletedCfgs:
		logsupport.Logs.Log("Local config library file {} no longer exists in archive".format(f))
	for l in PreOpFailure:
		logsupport.Logs.Log('PreOp Error: {}'.format(l), severity=logsupport.ConsoleWarning)
