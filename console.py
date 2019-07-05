#!/usr/bin/python -u
"""
Copyright 2016, 2017, 2018, 2019 Kevin Kahn

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
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

import cgitb
import datetime
import importlib

import signal
import sys
import time
import threading


# noinspection PyProtectedMember
from configobj import ConfigObj, Section

import config
import debug
import hubs.hubs
import screens.__screens as screens
import timers
from stores import mqttsupport, valuestore, localvarsupport, sysstore

config.sysStore = valuestore.NewValueStore(sysstore.SystemStore('System'))
config.sysStore.SetVal('ConsoleStartTime', time.time())

import configobjects
import atexit

import displayscreen
import exitutils
import hw
import hubs.isy.isy as isy
import hubs.ha.hasshub as hasshub
import logsupport
import maintscreen
import utilities
from logsupport import ConsoleWarning, ConsoleError

import alerttasks
from stores.weathprov.providerutils import SetUpTermShortener, WeathProvs
import screen
import historybuffer

'''
Constants
'''
configfilebase = "/home/pi/Console/"  # actual config file can be overridden from arg1
configfilelist = {}  # list of configfiles and their timestamps


logsupport.SpawnAsyncLogger()
HBMain = historybuffer.HistoryBuffer(40,'Main')
historybuffer.HBNet = historybuffer.HistoryBuffer(80, 'Net')

atexit.register(exitutils.exitlogging)

hubs.hubs.hubtypes['ISY'] = isy.ISY
hubs.hubs.hubtypes['HASS'] = hasshub.HA


# noinspection PyUnusedLocal
def handler(signum, frame):
	HBMain.Entry('Signal: {}'.format(signum))
	if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1):
		config.Running = False
		if signum == signal.SIGUSR1:
			logsupport.DevPrint('Watchdog termination')
			logsupport.Logs.Log("Console received a watchdog termination signal: {} - Exiting".format(signum), tb=True)
			config.terminationreason = 'watchdog termination'
			config.ecode = exitutils.WATCHDOGTERM
		else:
			logsupport.DevPrint('Signal termination {}'.format(signum))
			logsupport.Logs.Log("Console received termination signal: {} - Exiting".format(signum), tb=True)
			if signum == signal.SIGINT:
				config.terminationreason = 'interrupt signal'
				config.ecode = exitutils.EXTERNALSIGINT
			else:
				config.terminationreason = 'termination signal'
				config.ecode = exitutils.EXTERNALSIGTERM
			if config.sysStore.Watchdog_pid != 0: os.kill(config.sysStore.Watchdog_pid, signal.SIGUSR1)
			if config.sysStore.Topper_pid != 0: os.kill(config.sysStore.Topper_pid, signal.SIGKILL)
	else:
		logsupport.Logs.Log("Console received signal {} - Ignoring".format(signum))


signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGUSR1, handler)

config.sysStore.SetVal('Console_pid', os.getpid())
config.sysStore.SetVal('Watchdog_pid', 0)  # gets set for real later but for now make sure the variable exists
config.sysStore.SetVal('Topper_pid',0)
config.sysStore.SetVal('ExecDir', os.path.dirname(os.path.abspath(__file__)))
os.chdir(config.sysStore.ExecDir)  # make sure we are in the directory we are executing from
config.sysStore.SetVal('HomeDir', os.path.dirname(config.sysStore.ExecDir))
config.sysStore.SetVal('consolestatus','started')
logsupport.Logs.Log(u"Console ( " + str(config.sysStore.Console_pid) + u") starting in " + os.getcwd())
if len(sys.argv) == 2:
	config.sysStore.configfile = sys.argv[1]
elif os.path.isfile(configfilebase + "config.txt"):
	config.sysStore.configfile = configfilebase + "config.txt"
else:
	config.sysStore.configfile = configfilebase + "config-" + hw.hostname + ".txt"
sectionget = Section.get


def CO_get(self, key, default, delkey=True):
	try:
		rtn = sectionget(self, key, default)
		tmpr = rtn
		if isinstance(default, bool):
			rtn = rtn in ('True', 'true', 'TRUE', '1')
		if isinstance(default,
					  list):  # todo check this change carefuily.   Cases are [] which is list of strings, [val] which should be list of type(val)
			if len(default) == 0:  # its a string list
				if isinstance(rtn, str):
					rtn = [rtn]
			else:
				if isinstance(rtn, str):  # want list of <type> got single str so coerce to type and listify it
					rtn = [type(default[0])(rtn)]
				else:
					rtn = [type(default[0])(x) for x in rtn]
		elif default is not None:
			rtn = type(default)(rtn)

		if key in self and delkey:
			del self[key]
		# print('CO: {} {} T:{} typT:{} R:{} Tdf:{} TR:{}'.format(key, default,tmpr, type(tmpr),  rtn, type(default), type(rtn)))
		return rtn
	except Exception as E:  # todo delete prints
		print(
			'ZZ: {} {} T:{} typT:{} R:{} Tdf:{} TR:{} E: {}'.format(key, default, tmpr, type(tmpr), rtn, type(default),
																	type(rtn), repr(E)))


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
	print(u"Must run as root")
	# noinspection PyProtectedMember
	sys.exit(exitutils.EARLYABORT)

utilities.InitializeEnvironment()

logsupport.Logs.Log(u'Environment initialized on host ' + hw.hostname)

lastfn = u""
lastmod = 0

logsupport.Logs.Log('Exdir: {}  Pid: {}'.format(config.sysStore.ExecDir, str(config.sysStore.Console_pid)))

for root, dirs, files in os.walk(config.sysStore.ExecDir):
	for fname in files:
		if fname.endswith(u".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn

try:
	with open('{}/versioninfo'.format(config.sysStore.ExecDir)) as f:
		config.sysStore.SetVal('versionname',f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versionsha', f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versiondnld',f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versioncommit', f.readline()[:-1].rstrip())
except (IOError, ValueError):
	config.sysStore.SetVal('versionname', 'none')
	config.sysStore.SetVal('versionsha', 'none')
	config.sysStore.SetVal('versiondnld', 'none')
	config.sysStore.SetVal('versioncommit', 'none')

logsupport.Logs.Log(
	'Version/Sha/Dnld/Commit: {} {} {} {}'.format(config.sysStore.versionname, config.sysStore.versionsha, config.sysStore.versiondnld, config.sysStore.versioncommit))

"""
Dynamically load class definitions for all defined screen types, slert types, hubtypes, weather provider types
and link them to how configuration happens
"""
for screentype in os.listdir(os.getcwd() + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

logsupport.Logs.Log("Screen types imported")

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


logsupport.Logs.Log("Configuration file: " + config.sysStore.configfile)

if not os.path.isfile(config.sysStore.configfile):
	print("Abort - no configuration file found")
	logsupport.Logs.Log('Abort - no configuration file (' + hw.hostname + ')')
	exitutils.EarlyAbort('No Configuration File (' + hw.hostname + ')')

ParsedConfigFile = ConfigObj(config.sysStore.configfile)  # read the config.txt file

logsupport.Logs.Log("Parsed base config file")

configdir = os.path.dirname(config.sysStore.configfile)

configfilelist[config.sysStore.configfile] = os.path.getmtime(config.sysStore.configfile)

cfiles = []
pfiles = []
cfglib = ParsedConfigFile.get('cfglib', '')
if cfglib != '':
	cfglib += '/'
if cfglib[0] != '/':
	cfglib = configdir + '/' + cfglib
includes = ParsedConfigFile.get('include', [])
while includes:
	f = includes.pop(0)
	if f[0] != '/':
		pfiles.append('+' + f)
		f = cfglib + f
	else:
		pfiles.append(f)
	cfiles.append(f)
	# noinspection PyBroadException
	try:
		tmpconf = ConfigObj(f)
		includes = includes + tmpconf.get('include', [])
		ParsedConfigFile.merge(tmpconf)
		logsupport.Logs.Log("Merged config file " + f)
	except:
		logsupport.Logs.Log("Error merging include file: ", f)
	# noinspection PyBroadException
	try:
		configfilelist[f] = os.path.getmtime(f)
	except Exception as E:
		logsupport.Logs.Log("MISSING config file " + f)
		logsupport.Logs.Log('Excp: {}'.format(repr(E)))
		configfilelist[f] = 0

debug.InitFlags(ParsedConfigFile)

for nm, val in config.sysvals.items():
	config.sysStore.SetVal([nm], val[0](ParsedConfigFile.get(nm, val[1])))
	if val[2] is not None: config.sysStore.AddAlert(nm, val[2])
screen.InitScreenParams(ParsedConfigFile)

screens.ScaleScreensInfo()

logsupport.Logs.Log("Parsed globals")
logsupport.Logs.Log("Switching to real log")
logsupport.Logs = logsupport.InitLogs(hw.screen, os.path.dirname(config.sysStore.configfile))
cgitb.enable(format='text')
logsupport.Logs.Log(u"Soft ISY Console")

logsupport.Logs.Log(u"  \u00A9 Kevin Kahn 2016, 2017, 2018, 2019")
logsupport.Logs.Log("Software under Apache 2.0 License")
logsupport.Logs.Log("Version Information:")
logsupport.Logs.Log(" Running under Python: ", sys.version)
if not (sys.version_info[0] == 3 and sys.version_info[1] >= 5):
	logsupport.Logs.Log("Softconsole untested on Python versions earlier than 3.5 - please upgrade!",
						severity=ConsoleError, tb=False)
logsupport.Logs.Log(" Run from: ", config.sysStore.ExecDir)
logsupport.Logs.Log(" Last mod: ", lastfn)
logsupport.Logs.Log(" Mod at: ", time.ctime(lastmod))
logsupport.Logs.Log(" Tag: ", config.sysStore.versionname)
logsupport.Logs.Log(" Sha: ", config.sysStore.versionsha)
logsupport.Logs.Log(" How: ", config.sysStore.versiondnld)
logsupport.Logs.Log(" Version date: ", config.sysStore.versioncommit)
logsupport.Logs.Log("Start time: ", time.ctime(config.sysStore.ConsoleStartTime))
with open("{}/.ConsoleStart".format(config.sysStore.HomeDir), "w") as f:
	f.write(str(config.sysStore.ConsoleStartTime) + '\n')
logsupport.Logs.Log("Console Starting  pid: ", config.sysStore.Console_pid)
logsupport.Logs.Log("Host name: ", hw.hostname)
logsupport.Logs.Log("Screen type: ", hw.screentype)
logsupport.Logs.Log(
	'(Display device: {} Driver: {} Dim Method: {})'.format(os.environ['SDL_FBDEV'], os.environ['SDL_VIDEODRIVER'],
															hw.DimType))
logsupport.Logs.Log("Touch controller: {}".format(utilities.ts.controller))
logsupport.Logs.Log(
	"(Capacitive: {} Shifts: x: {} y: {} Flips: x: {} y: {} Scale: x: {} y: {})".format(utilities.ts._capscreen,
																						utilities.ts._shiftx,
																						utilities.ts._shifty,
																						utilities.ts._flipx,
																						utilities.ts._flipy,
																						utilities.ts._scalex,
																						utilities.ts._scaley))
logsupport.Logs.Log("Screen Orientation: ", ("Landscape", "Portrait")[hw.portrait])
if config.sysStore.PersonalSystem:
	logsupport.Logs.Log("Personal System")
if utilities.previousup > 0:
	logsupport.Logs.Log("Previous Console Lifetime: ", str(datetime.timedelta(seconds=utilities.previousup)))
if utilities.lastup > 0:
	logsupport.Logs.Log("Console Last Running at: ", time.ctime(utilities.lastup))
	logsupport.Logs.Log("Previous Console Downtime: ",
						str(datetime.timedelta(seconds=(config.sysStore.ConsoleStartTime - utilities.lastup))))
logsupport.Logs.Log("Main config file: ", config.sysStore.configfile,
					time.strftime(' %c', time.localtime(configfilelist[config.sysStore.configfile])))
logsupport.Logs.Log("Default config file library: ", cfglib)
logsupport.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	if configfilelist[f] == 0:
		logsupport.Logs.Log("  ", p, " No Such File", severity=ConsoleWarning)
	else:
		logsupport.Logs.Log("  ", p, time.strftime(' %c', time.localtime(configfilelist[f])))
debug.LogDebugFlags()

logsupport.LogLevel = int(ParsedConfigFile.get('LogLevel', logsupport.LogLevel))
logsupport.Logs.Log("Log level: ", logsupport.LogLevel)
screens.DS = displayscreen.DisplayScreen()  # create the actual device screen and touch manager

utilities.LogParams()
for n, param in config.sysvals.items():
	if param[3]:
		logsupport.Logs.Log('SysParam: ' + n + ": " + str(config.sysStore.GetVal(n)))

"""
Fake an ISY Hub section if old style auth present
"""
if "ISYaddr" in ParsedConfigFile:
	logsupport.Logs.Log("Converting ISYaddr parameter style to hub named: ", 'ISY')
	tmp = {"address": ParsedConfigFile.get("ISYaddr", ""),
		   "password": ParsedConfigFile.get("ISYpassword", ""),
		   "user": ParsedConfigFile.get("ISYuser", ""),
		   "type": "ISY"}
	ParsedConfigFile['ISY'] = tmp

"""
Pull out non-screen sections
"""
for i, v in ParsedConfigFile.items():
	if isinstance(v, Section):
		# noinspection PyArgumentList
		stype = v.get('type', '', delkey=False)
		if stype == 'MQTT':
			"""
			Set up mqtt brokers
			"""
			valuestore.NewValueStore(mqttsupport.MQTTBroker(i, v))
			del ParsedConfigFile[i]
		elif stype == "Locals":
			valuestore.NewValueStore(localvarsupport.LocalVars(i, v))
			del ParsedConfigFile[i]
		elif stype == "WeatherProvider":
			apikey = v.get('apikey', 'N/A')
			if i in WeathProvs:
				WeathProvs[i][1] = apikey
			else:
				logsupport.Logs.Log("No weather provider type: {}".format(i), severity=ConsoleWarning)
			del ParsedConfigFile[i]
		for hubtyp, pkg in hubs.hubs.hubtypes.items():
			if stype == hubtyp:
				# noinspection PyBroadException
				try:
					hubs.hubs.Hubs[i] = pkg(i, v.get('address', ''), v.get('user', ''), v.get('password', ''))
				except BaseException as e:
					logsupport.Logs.Log("Fatal console error - fix config file: ", e, severity=ConsoleError, tb=False)
					exitutils.Exit(exitutils.ERRORDIE, immediate=True)  # shutdown and don't try restart
				del ParsedConfigFile[i]

from stores import genericweatherstore

for i, v in ParsedConfigFile.items():
	if isinstance(v, Section):
		# noinspection PyArgumentList
		stype = v.get('type', '', delkey=False)  #todo check no type param
		loccode = '*unset*'
		for wptyp, info in WeathProvs.items():
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
				del ParsedConfigFile[i]

if screen.screenStore.GetVal('DefaultHub') == '':
	if len(hubs.hubs.Hubs) == 1:
		nm = list(hubs.hubs.Hubs.keys())[0]
		screen.screenStore.SetVal('DefaultHub', nm)
		hubs.hubs.defaulthub = hubs.hubs.Hubs[nm]  # grab the only element
		logsupport.Logs.Log("Default (only) hub is: ", nm)
	else:
		logsupport.Logs.Log("No default Hub specified", severity=ConsoleWarning)
		hubs.hubs.defaulthub = None
else:
	try:
		nm = screen.screenStore.GetVal('DefaultHub')
		hubs.hubs.defaulthub = hubs.hubs.Hubs[nm]
		logsupport.Logs.Log("Default hub is: ", nm)
	except KeyError:
		logsupport.Logs.Log("Specified default Hub doesn't exist", severity=ConsoleWarning)
		hubs.hubs.defaulthub = None

"""
Set up screen Tokens
"""
screen.BACKTOKEN = screen.ScreenDesc({}, '***BACK***')
screen.HOMETOKEN = screen.ScreenDesc({}, '***HOME***')
screen.SELFTOKEN = screen.ScreenDesc({}, '***SELF***')

"""
Set up alerts and local variables
"""
alertspeclist = {}
for n, hub in hubs.hubs.Hubs.items():
	alertspeclist.update(hub.alertspeclist)

if 'Alerts' in ParsedConfigFile:
	alertspec = ParsedConfigFile['Alerts']
	del ParsedConfigFile['Alerts']
else:
	alertspec = ConfigObj()

alertspec.merge(alertspeclist)

if 'Variables' in ParsedConfigFile:
	valuestore.NewValueStore(localvarsupport.LocalVars('LocalVars', ParsedConfigFile['Variables']))
	i = 0
	tn = ['LocalVars', '']
	for nm, val in ParsedConfigFile['Variables'].items():
		logsupport.Logs.Log("Local variable: " + nm + "(" + str(i) + ") = " + str(val))
		tn[1] = nm
		valuestore.SetVal(tn, val)
		i += 1
	del ParsedConfigFile['Variables']

"""
Build the Hub(s) object structure and connect the configured screens to it
"""
configobjects.MyScreens(ParsedConfigFile)
logsupport.Logs.Log("Linked config to Hubs")

"""
Build the alerts structures
"""
alerttasks.AlertItems = alerttasks.Alerts(alertspec)
logsupport.Logs.Log("Alerts established")

"""
Set up the Maintenance Screen
"""
maintscreen.SetUpMaintScreens()
logsupport.Logs.Log("Built Maintenance Screen")

LogBadParams(ParsedConfigFile, "Globals")
LogBadParams(alertspec, "Alerts")
"""
Dump documentation if development version
"""
# if config.sysStore.versionname == 'development':
#	utilities.DumpDocumentation()

"""
Run the main console loop
"""
for n in alerttasks.monitoredvars:  # make sure vars used in alerts are updated to starting values
	valuestore.GetVal(n)
config.sysStore.ErrorNotice = -1
gui = threading.Thread(name='GUI', target=screens.DS.MainControlLoop, args=(screens.HomeScreen,))
config.ecode = 99
gui.start()

gui.join()
logsupport.Logs.Log("Main line exit: ", config.ecode)
timers.ShutTimers(config.terminationreason)
logsupport.Logs.Log('Console exiting')
hw.GoBright(100)
pygame.quit()
logsupport.DevPrint('Exit handling done')

sys.exit(config.ecode)