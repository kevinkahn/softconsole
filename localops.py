import os
import shutil
import config
import logsupport
import subprocess

PreOpScripts = []
NewCfgs = set()
DeletedCfgs = set()
CopiedConfig = ''
PreOpFailure = []


# this file is my personal example of a localops module (and will run on any system marked as homesystem)
# to provide your own build a localops.py in your home directory - i.e. the parent of the directory that
# the console source lives in.  Any module there will not be overwritten

def PreOp():
	global DeletedCfgs, CopiedConfig, NewCfgs, PreOpFailure
	if not os.path.exists(config.sysStore.HomeDir + '/homesystem'):
		return

	confserver = '/home/pi/.exconfs/'
	conflocal = config.sysStore.configdir + '/cfglib/'
	cfgdirserver = confserver + 'cfglib/'
	newerlocal = config.sysStore.configdir + '/newer/'
	oldlocal = config.sysStore.configdir + '/old/'
	try:
		os.mkdir(newerlocal)
	except Exception:
		pass
	try:
		os.mkdir(oldlocal)
	except Exception:
		pass

	try:
		if os.path.exists(confserver + "runalways.sh"):
			print("always")
			cp = subprocess.run('bash ' + confserver + "runalways.sh", stdout=subprocess.PIPE,
								stderr=subprocess.STDOUT, text=True, shell=True)
			PreOpScripts.append('------runalways---------')
			PreOpScripts.append('Return code {}'.format(cp.returncode))
			if cp.returncode != 0:
				PreOpFailure.append('Error in runalways script')
			for ln in cp.stdout.split('\n'):
				PreOpScripts.append(ln)
			PreOpScripts.append('---------------')
		else:
			PreOpScripts.append('No runalways script found')
	except Exception as E:
		PreOpScripts.append('Exception in runalways script handling: ({})'.format(E))

	try:
		if os.path.exists(confserver + "runonce.sh"):
			try:
				rtime = os.path.getmtime(config.sysStore.configdir + '/runonce.sh.done')
			except Exception:
				rtime = 0
			if rtime == os.path.getmtime(confserver + 'runonce.sh'):
				# already run
				PreOpScripts.append('Run once already run')
			else:
				PreOpScripts.append('Do a run once')
				try:
					os.remove(config.sysStore.configdir + '/runonce.sh.done')
				except:
					pass
				shutil.copy2(confserver + 'runonce.sh', config.sysStore.configdir + '/runonce.sh')
				cp = subprocess.run('bash ' + config.sysStore.configdir + '/runonce.sh', stdout=subprocess.PIPE,
									stderr=subprocess.STDOUT, text=True, shell=True)
				PreOpScripts.append('-------runonce--------')
				PreOpScripts.append('Return code {}'.format(cp.returncode))
				if cp.returncode != 0:
					PreOpFailure.append('Error in runonce script')
				for ln in cp.stdout.split('\n'):
					PreOpScripts.append(ln)
				PreOpScripts.append('---------------')
				os.rename(config.sysStore.configdir + '/runonce.sh', config.sysStore.configdir + '/runonce.sh.done')
		else:
			PreOpScripts.append('No runonce script found')
	except Exception as E:
		PreOpScripts.append('Exception in runonce script handling: ({})'.format(E))

	try:
		cfgliblocal = set([f for f in os.listdir(conflocal) if os.path.isfile(os.path.join(conflocal, f))])
		cfglibserver = set([f for f in os.listdir(cfgdirserver) if os.path.isfile(os.path.join(cfgdirserver, f))])
	except Exception as E:
		PreOpFailure.append("Getting cfglists ({})".format(E))
		cfgliblocal = set()
		cfglibserver = set()

	reftime = os.path.getmtime('console.py')  # use as install time of the console tar
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
				if mtloc != reftime:
					shutil.copy2(conflocal + f, newerlocal)
					shutil.copy2(cfgdirserver + f, conflocal + f)
					PreOpFailure.append('Newer cfglib file on local system: {}'.format(f))
				else:
					print('Not saving "newer" file from version installation {}'.format(f))  # todo del
		DeletedCfgs = cfgliblocal - cfglibserver
		for f in DeletedCfgs:
			shutil.move(conflocal + f, oldlocal)
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
	for l in PreOpScripts:
		logsupport.Logs.Log('PreOp Script: {}'.format(l))
	for f in NewCfgs:
		logsupport.Logs.Log("Updated cfg library element: {}".format(f))
	if CopiedConfig != "":
		logsupport.Logs.Log("Updated host config file: {}".format(CopiedConfig))
	for f in DeletedCfgs:
		logsupport.Logs.Log("Local config library file {} no longer exists in archive".format(f))
	for l in PreOpFailure:
		logsupport.Logs.Log('PreOp Error: {}'.format(l), severity=logsupport.ConsoleWarning)
	logsupport.Logs.Log('-----Local Ops Complete-----')
