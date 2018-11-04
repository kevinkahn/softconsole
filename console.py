#!/usr/bin/python -u
# above assumes it points at python 2.7 and may not be portable
"""
Copyright 2016, 2017, 2018 Kevin Kahn

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

	   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import cgitb
import datetime
import importlib
import os
import signal
import sys
import time

import pygame
# noinspection PyProtectedMember
from configobj import ConfigObj, Section

import config
import configobjects
import atexit
import debug
import displayscreen
import exitutils
import globalparams
import hw
import isy
import logsupport
import maintscreen
import utilities
from logsupport import ConsoleWarning,ConsoleError
from stores import mqttsupport, valuestore, localvarsupport, sysstore
import alerttasks
from stores.weathprov.providerutils import SetUpTermShortener


class ExitHooks(object):
	def __init__(self):
		self.exit_code = None
		self.exception = None
		self._orig_exit = None

	def hook(self):
		self._orig_exit = sys.exit
		sys.exit = self.exit
		sys.excepthook = self.exc_handler

	def exit(self, code=0):
		self.exit_code = code
		self._orig_exit(code)

	def exc_handler(self, exc_type, exc, *args):
		self.exception = exc
		sys.__excepthook__(exc_type, exc, args)


config.hooks = ExitHooks()
config.hooks.hook()
atexit.register(exitutils.exitlogging)

config.hubtypes['ISY'] = isy.ISY
if sys.version_info[0] == 3:  # todo remove and force v3.5
	import hasshub
	config.hubtypes['HASS'] = hasshub.HA

# noinspection PyUnusedLocal
def handler(signum, frame):
	if signum in (signal.SIGTERM, signal.SIGINT):
		logsupport.Logs.Log(u"Console received a termination signal ", str(signum), u" - Exiting")
		hw.GoBright(100)
		pygame.display.quit()
		pygame.quit()
		# noinspection PyProtectedMember
		# os._exit(0)
		sys.exit(0)
	else:
		logsupport.Logs.Log(u"Console received signal " + str(signum) + u" Ignoring")


signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

config.sysStore = valuestore.NewValueStore(sysstore.SystemStore('System'))

config.Console_pid = os.getpid()
config.exdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(config.exdir)  # make sure we are in the directory we are executing from
config.homedir = os.path.dirname(config.exdir)
logsupport.Logs.Log(u"Console (" + str(config.Console_pid) + u") starting in " + os.getcwd())

sectionget = Section.get


def CO_get(self, key, default, delkey=True):
	rtn = sectionget(self, key, default)
	if key in self and delkey:
		del self[key]
	return rtn


Section.get = CO_get


def LogBadParams(section, name):
	for thisnm, s in section.items():
		if isinstance(s, Section):
			LogBadParams(s, thisnm)
		else:
			logsupport.Logs.Log(u"Bad (unused) parameter name in: ", name, u" (", thisnm, u"=", str(s), u")",
								severity=ConsoleWarning)


if os.getegid() != 0:
	# Not running as root
	logsupport.Logs.Log(u"Not running as root - exit")
	print (u"Must run as root")
	# noinspection PyProtectedMember
	sys.exit(exitutils.EARLYABORT)
#os._exit(exitutils.EARLYABORT)

utilities.InitializeEnvironment()

logsupport.Logs.Log(u'Environment initialized on host ' + config.hostname)

lastfn = u""
lastmod = 0
config.Console_pid = os.getpid()

logsupport.Logs.Log(u'Exdir: ' + config.exdir + u'  Pid: ' + str(config.Console_pid))

for root, dirs, files in os.walk(config.exdir):
	for fname in files:
		if fname.endswith(u".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn

try:
	with open(config.exdir + u'/' + u'versioninfo') as f:
		config.versionname = f.readline()[:-1].rstrip()
		config.versionsha = f.readline()[:-1].rstrip()
		config.versiondnld = f.readline()[:-1].rstrip()
		config.versioncommit = f.readline()[:-1].rstrip()
except (IOError, ValueError):
	config.versionname = u'none'
	config.versionsha = u'none'
	config.versiondnld = u'none'
	config.versioncommit = u'none'

logsupport.Logs.Log(
	u'Version/Sha/Dnld/Commit: ' + config.versionname + u' ' + config.versionsha + u' ' + config.versiondnld + u' ' + config.versioncommit)


"""
Dynamically load class definitions for all defined screen types and link them to how configuration happens
"""
for screentype in os.listdir(os.getcwd() + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

logsupport.Logs.Log("Screen types imported")

# for alertproctype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/alerts'):
for alertproctype in os.listdir(os.getcwd() + '/alerts'):
	if '__' not in alertproctype:
		splitname = os.path.splitext(alertproctype)
		if splitname[1] == '.py':
			importlib.import_module('alerts.' + splitname[0])

logsupport.Logs.Log("Alert Proc types imported")

# load weather providers
for wp in os.listdir(os.getcwd() + '/stores/weathprov'):
	if '__' not in wp:
		splitname = os.path.splitext(wp)
		if splitname[1] == '.py':
			importlib.import_module('stores.weathprov.' + splitname[0])
logsupport.Logs.Log("Weather providers imported")

for n in alerttasks.alertprocs:
	alerttasks.alertprocs[n] = alerttasks.alertprocs[n]()  # instantiate an instance of each alert class

logsupport.Logs.Log("Alert classes instantiated")

"""
Initialize the Console
"""

SetUpTermShortener()

if len(sys.argv) == 2:
	config.configfile = sys.argv[1]
elif os.path.isfile(config.configfilebase + "config.txt"):
	config.configfile = config.configfilebase + "config.txt"
else:
	config.configfile = config.configfilebase + "config-" + config.hostname + ".txt"

logsupport.Logs.Log("Configuration file: " + config.configfile)

if not os.path.isfile(config.configfile):
	print ("Abort - no configuration file found")
	logsupport.Logs.Log('Abort - no configuration file (' + config.hostname + ')')
	exitutils.EarlyAbort('No Configuration File (' + config.hostname + ')')

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file

logsupport.Logs.Log("Parsed base config file")

configdir = os.path.dirname(config.configfile)

config.configfilelist[config.configfile] = os.path.getmtime(config.configfile)

cfiles = []
pfiles = []
cfglib = config.ParsedConfigFile.get('cfglib', '')
if cfglib != '':
	cfglib += '/'
if cfglib[0] != '/':
	cfglib = configdir + '/' + cfglib
includes = config.ParsedConfigFile.get('include', [])
while includes:
	f = includes.pop(0)
	if f[0] != '/':
		pfiles.append('+' + f)
		f = cfglib + f
	else:
		pfiles.append(f)
	cfiles.append(f)
	try:
		tmpconf = ConfigObj(f)
		includes = includes + tmpconf.get('include', [])
		config.ParsedConfigFile.merge(tmpconf)
		logsupport.Logs.Log("Merged config file " + f)
	except:
		logsupport.Logs.Log("Error merging include file: ", f)
	# noinspection PyBroadException
	try:
		config.configfilelist[f] = os.path.getmtime(f)
	except:
		logsupport.Logs.Log("MISSING config file " + f)
		config.configfilelist[f] = 0

debug.InitFlags(config.ParsedConfigFile)



utilities.ParseParam(globalparams, config.ParsedConfigFile)  # add global parameters to config file
for nm, val in config.sysvals.items():
	config.sysStore.SetVal([nm], val[0](config.ParsedConfigFile.get(nm, val[1])))
	if val[2] is not None: config.sysStore.AddAlert(nm, val[2])

logsupport.Logs.Log("Parsed globals")
logsupport.Logs.Log("Switching to real log")
logsupport.Logs = logsupport.InitLogs(config.screen, os.path.dirname(config.configfile))
cgitb.enable(format='text')
logsupport.Logs.Log(u"Soft ISY Console")

logsupport.Logs.Log(u"  \u00A9 Kevin Kahn 2016, 2017, 2018")
logsupport.Logs.Log("Software under Apache 2.0 License")
logsupport.Logs.Log("Version Information:")
logsupport.Logs.Log(" Running under Python: ", sys.version)
if not (sys.version_info[0] == 3 and sys.version_info[1] >= 5):
	logsupport.Logs.Log("Softconsole untested on Python versions earlier than 3.5 - please upgrade!",
						severity=ConsoleError, tb=False)
logsupport.Logs.Log(" Run from: ", config.exdir)
logsupport.Logs.Log(" Last mod: ", lastfn)
logsupport.Logs.Log(" Mod at: ", time.ctime(lastmod))
logsupport.Logs.Log(" Tag: ", config.versionname)
logsupport.Logs.Log(" Sha: ", config.versionsha)
logsupport.Logs.Log(" How: ", config.versiondnld)
logsupport.Logs.Log(" Version date: ", config.versioncommit)
logsupport.Logs.Log("Start time: ", time.ctime(config.starttime))
with open(config.homedir + "/.ConsoleStart", "w") as f:
	f.write(str(config.starttime) + '\n')
logsupport.Logs.Log("Console Starting  pid: ", config.Console_pid)
logsupport.Logs.Log("Host name: ", config.hostname)
logsupport.Logs.Log("Screen type: ", config.screentype)
logsupport.Logs.Log("Screen Orientation: ", ("Landscape", "Portrait")[config.portrait])
if config.personalsystem:
	logsupport.Logs.Log("Personal System")
if config.previousup > 0:
	logsupport.Logs.Log("Previous Console Lifetime: ", str(datetime.timedelta(seconds=config.previousup)))
if config.lastup > 0:
	logsupport.Logs.Log("Console Last Running at: ", time.ctime(config.lastup))
	logsupport.Logs.Log("Previous Console Downtime: ",
						str(datetime.timedelta(seconds=(config.starttime - config.lastup))))
logsupport.Logs.Log("Main config file: ", config.configfile,
					time.strftime(' %c', time.localtime(config.configfilelist[config.configfile])))
logsupport.Logs.Log("Default config file library: ", cfglib)
logsupport.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	if config.configfilelist[f] == 0:
		logsupport.Logs.Log("  ", p, " No Such File", severity=ConsoleWarning)
	else:
		logsupport.Logs.Log("  ", p, time.strftime(' %c', time.localtime(config.configfilelist[f])))
debug.LogDebugFlags()

logsupport.LogLevel = int(config.ParsedConfigFile.get('LogLevel', logsupport.LogLevel))
logsupport.Logs.Log("Log level: ", logsupport.LogLevel)
config.DS = displayscreen.DisplayScreen()  # create the actual device screen and touch manager

utilities.LogParams()
for i in config.sysStore:
	logsupport.Logs.Log('SysParam: ' + valuestore.ExternalizeVarName(i.name) + ": " + str(i.Value))

"""
Fake an ISY Hub section if old style auth present
"""
if "ISYaddr" in config.ParsedConfigFile:
	logsupport.Logs.Log("Converting ISYaddr parameter style to hub named: ", config.defaultISYname)
	tmp = {"address":config.ParsedConfigFile.get("ISYaddr",""),
					 "password":config.ParsedConfigFile.get("ISYpassword",""),
					 "user":config.ParsedConfigFile.get("ISYuser",""),
					 "type":"ISY"}
	config.ParsedConfigFile[config.defaultISYname] = tmp

"""
Pull out non-screen sections
"""
for i, v in config.ParsedConfigFile.items():
	if isinstance(v, Section):
		# noinspection PyArgumentList
		stype = v.get('type', None, delkey=False)
		if stype == 'MQTT':
			"""
			Set up mqtt brokers
			"""
			valuestore.NewValueStore(mqttsupport.MQTTBroker(i, v))
			del config.ParsedConfigFile[i]
		elif stype == "Locals":
			valuestore.NewValueStore(localvarsupport.LocalVars(i, v))
			del config.ParsedConfigFile[i]
		elif stype == "WeatherProvider":
			apikey = v.get('apikey', 'N/A')
			config.WeathProvs[i][1] = apikey
			del config.ParsedConfigFile[i]
		for hubtyp, pkg in config.hubtypes.items():
			if stype == hubtyp:
				# noinspection PyBroadException
				try:
					config.Hubs[i] = pkg(i, v.get('address',''), v.get('user',''), v.get('password',''))
				except BaseException as e:
					logsupport.Logs.Log("Fatal console error - fix config file: ", e, severity=ConsoleError, tb=False)
					exitutils.Exit(exitutils.ERRORDIE, immediate=True)  # shutdown and don't try restart
				del config.ParsedConfigFile[i]

from stores import genericweatherstore

for i, v in config.ParsedConfigFile.items():
	if isinstance(v, Section):
		stype = v.get('type', None, delkey=False)
		for wptyp, info in config.WeathProvs.items():
			if stype == wptyp:
				try:
					desc = i
					loccode = v.get('location', desc)
					refresh = int(v.get('refresh', 60))  # default refresh in minutes
					ws = info[0](desc, loccode, info[1])
					valuestore.NewValueStore(genericweatherstore.WeatherVals(desc, ws, refresh))
				except Exception as e:
					logsupport.Logs.Log('Unhandled error creating weather location: ', loccode, repr(e),
										severity=ConsoleError, tb=False)
				del config.ParsedConfigFile[i]



config.defaulthubname = config.ParsedConfigFile.get('DefaultHub','')

if config.defaulthubname == '':  # todo handle no hub case for screen testing
	if len(config.Hubs) == 1:
		config.defaulthubname = list(config.Hubs.keys())[0]
		config.defaulthub = config.Hubs[config.defaulthubname] # grab the only element
		logsupport.Logs.Log("Default (only) hub is: ", config.defaulthubname)
	else:
		logsupport.Logs.Log("No default Hub specified", severity=ConsoleWarning)
		config.defaulthub = None
else:
	try:
		config.defaulthub = config.Hubs[config.defaulthubname]
		logsupport.Logs.Log("Default hub is: ", config.defaulthubname)
	except KeyError:
		logsupport.Logs.Log("Specified default Hub doesn't exist", severity=ConsoleWarning)
		config.defaulthub = None



"""
Set up alerts and local variables
"""
alertspeclist = {}
for n, hub in config.Hubs.items():
	alertspeclist.update(hub.alertspeclist)

if 'Alerts' in config.ParsedConfigFile:
	alertspec = config.ParsedConfigFile['Alerts']
	del config.ParsedConfigFile['Alerts']
else:
	alertspec = ConfigObj()

alertspec.merge(alertspeclist)

if 'Variables' in config.ParsedConfigFile:
	valuestore.NewValueStore(localvarsupport.LocalVars('LocalVars', config.ParsedConfigFile['Variables']))
	i = 0
	tn = ['LocalVars', '']
	for nm, val in config.ParsedConfigFile['Variables'].items():
		logsupport.Logs.Log("Local variable: " + nm + "(" + str(i) + ") = " + str(val))
		tn[1] = nm
		valuestore.SetVal(tn, val)
		valuestore.SetAttr(tn, (3, i))
		i += 1
	del config.ParsedConfigFile['Variables']

"""
Build the Hub(s) object structure and connect the configured screens to it
"""

configobjects.MyScreens()
logsupport.Logs.Log("Linked config to Hubs")

"""
Build the alerts structures
"""
config.Alerts = alerttasks.Alerts(alertspec)
logsupport.Logs.Log("Alerts established")

"""
Set up the Maintenance Screen
"""
maintscreen.SetUpMaintScreens()
logsupport.Logs.Log("Built Maintenance Screen")

LogBadParams(config.ParsedConfigFile, "Globals")
LogBadParams(alertspec, "Alerts")
"""
Dump documentation if development version
"""
#if config.versionname == 'development':
#	utilities.DumpDocumentation()

"""
Run the main console loop
"""
for n in alerttasks.monitoredvars:  # make sure vars used in alerts are updated to starting values
	valuestore.GetVal(n)
logsupport.ErrorNotice = -1  # if -1 no unseen, else entry number of first unseen
config.DS.MainControlLoop(config.HomeScreen)
logsupport.Logs.Log("Main line exit: ", config.ecode)
pygame.quit()
# noinspection PyProtectedMember
sys.exit(config.ecode)
#os._exit(config.ecode)

# This never returns
