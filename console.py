#!/home/pi/pyenv/bin/python -u
"""
Copyright 2016, 2017, 2018, 2019, 2020, 2021 Kevin Kahn

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
import subprocess
import traceback

from setproctitle import setproctitle

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from guicore.screencallmanager import pg
from utils import tracebackplus

import datetime

import signal
import sys
import time
import threading

# noinspection PyProtectedMember
from configobj import ConfigObj, Section

import config
import debug

import screens.__screens as screens
from utils import timers, utilities, displayupdate, hw, exitutils, utilfuncs
from stores import mqttsupport, valuestore, localvarsupport, sysstore

config.sysStore = valuestore.NewValueStore(sysstore.SystemStore('System'))
config.sysStore.SetVal('ConsoleStartTime', time.time())

import configobjects
import atexit

from guicore import displayscreen

import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail

from alertsystem import alerttasks
from stores.weathprov.providerutils import SetUpTermShortener, WeathProvs
from screens import screen, maintscreen
import historybuffer
import controlevents



config.sysStore.SetVal('ExecDir', os.path.dirname(os.path.abspath(__file__)))
config.sysStore.SetVal('HomeDir', os.path.dirname(config.sysStore.ExecDir))
if os.path.exists(config.sysStore.HomeDir + '/.permissionchanges'):
	with open(config.sysStore.HomeDir + '/.permissionchanges', 'r') as f:
		perms = f.readlines()
	for l in perms:
		res = subprocess.call(l, shell=True)
		logsupport.Logs.Log('Set permission {} Result; {}'.format(l, res))


'''
Constants
'''
configfilebase = "/home/pi/Console/"  # actual config file can be overridden from arg1
from config import configfilelist  # list of configfiles and their timestamps

setproctitle('Console Main')

logsupport.SpawnAsyncLogger()
HBMain = historybuffer.HistoryBuffer(40, 'Main')
historybuffer.HBNet = historybuffer.HistoryBuffer(80, 'Net')

atexit.register(exitutils.exitlogging)


# noinspection PyUnusedLocal
def handler(signum, frame):
	HBMain.Entry('Signal: {}'.format(signum))
	if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1):
		config.terminationreason = exitutils.reasonmap[signum][0]
		config.ecode = exitutils.reasonmap[signum][1]
		if not config.Running and not config.Exiting:
			# interrupt before gui is started so just exit here
			logsupport.Logs.Log("Exit during startup: {}".format(config.ecode))
			timers.ShutTimers(config.terminationreason)
			logsupport.Logs.Log('Console exiting')
			hw.GoBright(100)
			pg.quit()
			sys.exit(config.ecode)
		config.Running = False
		if signum == signal.SIGUSR1 and not config.Exiting:
			logsupport.DevPrint('Watchdog termination')
			logsupport.Logs.Log("Console received a watchdog termination signal: {} - Exiting(1)".format(signum),
								tb=True)
			if config.sysStore.Watchdog_pid != 0: os.kill(config.sysStore.Watchdog_pid, signal.SIGUSR1)
		elif not config.Exiting:
			logsupport.DevPrint('Signal termination {}'.format(signum))
			logsupport.Logs.Log("Console received termination signal: {} - Exiting(2)".format(signum))
			if config.sysStore.Watchdog_pid != 0: os.kill(config.sysStore.Watchdog_pid, signal.SIGUSR1)
			if config.sysStore.Topper_pid != 0: os.kill(config.sysStore.Topper_pid, signal.SIGKILL)

	else:
		if config.Running:
			logsupport.Logs.Log("Console received signal {} - Ignoring".format(signum))
		else:
			print('Development environment exit')
			if config.sysStore.Watchdog_pid != 0: os.kill(config.sysStore.Watchdog_pid, signal.SIGUSR1)
			if config.sysStore.Topper_pid != 0: os.kill(config.sysStore.Topper_pid, signal.SIGKILL)
			sys.exit(999)



signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGUSR1, handler)

config.sysStore.SetVal('Console_pid', os.getpid())
config.sysStore.SetVal('Watchdog_pid', 0)  # gets set for real later but for now make sure the variable exists
config.sysStore.SetVal('Topper_pid',0)
os.chdir(config.sysStore.ExecDir)  # make sure we are in the directory we are executing from
config.sysStore.SetVal('consolestatus', 'started')
config.sysStore.SetVal('hostname', hw.hostname)
logsupport.Logs.Log(u"Console ( " + str(config.sysStore.Console_pid) + u") starting in " + os.getcwd())
if len(sys.argv) == 2:
	config.sysStore.configfile = sys.argv[1]
elif os.path.isfile(configfilebase + "config.txt"):
	config.sysStore.configfile = configfilebase + "config.txt"
else:
	config.sysStore.configfile = configfilebase + "config-" + hw.hostname + ".txt"

configdir = os.path.dirname(config.sysStore.configfile)
config.sysStore.configdir = configdir

# Wait to import/initialize hubs until config info above is set so can use (e.g., HA params)
import hubs.hubs
import hubs.isy.isy as isy
import hubs.ha.hasshub as hasshub
import hubs.missing.missinghub as missinghub

hubs.hubs.hubtypes['ISY'] = isy.ISY
hubs.hubs.hubtypes['ISYDummy'] = isy.ISY
hubs.hubs.hubtypes['HASS'] = hasshub.HA
hubs.hubs.hubtypes['*missing*'] = missinghub.Hub

try:
	with open('{}/versioninfo'.format(config.sysStore.ExecDir)) as f:
		config.sysStore.SetVal('versionname', f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versionsha', f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versiondnld', f.readline()[:-1].rstrip())
		config.sysStore.SetVal('versioncommit', f.readline()[:-1].rstrip())
except (IOError, ValueError):
	config.sysStore.SetVal('versionname', 'none')
	config.sysStore.SetVal('versionsha', 'none')
	config.sysStore.SetVal('versiondnld', 'none')
	config.sysStore.SetVal('versioncommit', 'none')

if config.sysStore.versionname == 'development': utilfuncs.isdevsystem = True
if config.sysStore.versionname == 'homerelease': utilfuncs.ishomesystem = True

try:
	sys.path.insert(0, '../')  # search for a localops module first in the home dir then one up
	import localops

	del sys.path[0]  # don't leave junk in search path
	localops.PreOp()
except Exception as E:
	logsupport.Logs.Log('No local ops module ({})'.format(E), severity=ConsoleDetail)

sectionget = Section.get


def CO_get(self, key, default, delkey=True):
	try:
		rtn = sectionget(self, key, default)
		if isinstance(default, bool) and isinstance(rtn, str):
			rtn = rtn in ('True', 'true', 'TRUE', '1')
		if isinstance(default,
					  list):  # todo check this change carefuily.   Cases are [] which is list of strings, [val] which should be list of type(val)
			if len(default) == 0:  # it's a string list
				if isinstance(rtn, str):
					rtn = [rtn]
			else:
				if isinstance(rtn, str):  # want list of <type> got single str so coerce to type and listify it
					rtn = [type(default[0])(rtn)]
				else:
					# noinspection PyTypeChecker
					rtn = [type(default[0])(x) for x in rtn]
		elif default is not None:
			rtn = type(default)(rtn)

		if key in self and delkey:
			del self[key]
		return rtn
	except Exception as Eco:
		logsupport.Logs.Log(
			'Internal exception in handling config param get: key {} default {} exc: {}'.format(key, default, Eco),
			severity=ConsoleError)


Section.get = CO_get


def LogBadParams(section, name):
	if section not in utilities.ErroredConfigSections:
		for thisnm, s in section.items():
			if isinstance(s, Section):
				LogBadParams(s, thisnm)
			else:
				logsupport.Logs.Log("Bad (unused) parameter name in: {} ({}={})".format(name, thisnm, str(s)),
									severity=ConsoleWarning)


def CheckForTempConfigVersion(directory, fo):
	if utilfuncs.isdevsystem:
		# override config file with a working version if it exists
		foveride = fo + 'x'
		if os.path.exists(directory + foveride):
			logsupport.Logs.Log('Use temp version of config file: {}'.format(f))
			fo = foveride
	return fo

try:
	utilities.InitializeEnvironment()
except Exception as E:
	logsupport.Logs.Log('HW Config Exception: {}'.format(E))
	exitutils.EarlyAbort('HW Config Issue', screen=False)

logsupport.Logs.Log(u'Environment initialized on host ' + hw.hostname)
if 'Zero' in hw.hwinfo:
	controlevents.LateTolerance = 4.0

lastfn = u""
lastmod = 0

logsupport.Logs.Log('Exdir: {}  Pid: {}'.format(config.sysStore.ExecDir, str(config.sysStore.Console_pid)))

with open('../running', 'w') as f:
	print('Running at {}'.format(time.time()), file=f)

for root, dirs, files in os.walk(config.sysStore.ExecDir):
	for fname in files:
		if fname.endswith(u".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn
####


logsupport.Logs.Log(
	'Version/Sha/Dnld/Commit: {} {} {} {}'.format(config.sysStore.versionname, config.sysStore.versionsha, config.sysStore.versiondnld, config.sysStore.versioncommit))

"""
Dynamically load class definitions for all defined screen types, alert types, hubtypes, weather provider types
and link them to how configuration happens
"""

utilfuncs.importmodules('screens/specificscreens')
logsupport.Logs.Log("Screen types imported")

utilfuncs.importmodules('alerts')
logsupport.Logs.Log("Alert Proc types imported")

utilfuncs.importmodules('stores/weathprov')
logsupport.Logs.Log("Weather providers imported")

for n in alerttasks.alertprocs:
	alerttasks.alertprocs[n] = alerttasks.alertprocs[n]()  # instantiate an instance of each alert class

logsupport.Logs.Log("Alert classes instantiated")

"""
Initialize the Console
"""
# clear the systemd hack once started
signal.signal(signal.SIGHUP, handler)


SetUpTermShortener()


logsupport.Logs.Log("Configuration file: " + config.sysStore.configfile)

if not os.path.isfile(config.sysStore.configfile):
	print("Abort - no configuration file found")
	logsupport.Logs.Log('Abort - no configuration file (' + hw.hostname + ')')
	exitutils.EarlyAbort('No Configuration File (' + hw.hostname + ')')

ParsedConfigFile = ConfigObj(config.sysStore.configfile)  # read the config.txt file

logsupport.Logs.Log("Parsed base config file")

configfilelist[config.sysStore.configfile] = os.path.getmtime(config.sysStore.configfile)

cfiles = []
pfiles = []
cfglib = ParsedConfigFile.get('cfglib', '')
if cfglib != '':
	cfglib += '/'
if cfglib[0] != '/':
	cfglib = configdir + '/' + cfglib
includes = ParsedConfigFile.get('include', [])

if utilfuncs.isdevsystem:
	for cfgfile in os.listdir(cfglib):
		if cfgfile.endswith('.cfg'):
			if cfgfile not in includes:
				print('Autoadd {} to includes for development'.format(cfgfile))
				includes.append(cfgfile)
	if os.path.exists(cfglib + 'devsys.ovr'):
		includes.append(cfglib + 'devsys.ovr')

while includes:
	f = includes.pop(0)
	if f[0] != '/':
		f = CheckForTempConfigVersion(cfglib, f)
		pfiles.append('+' + f)
		f = cfglib + f
	else:
		f = CheckForTempConfigVersion('', f)
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
'''
confserver = '/home/pi/.exconfs/'
cfgdirserver = confserver + 'cfglib/'
for f, ftime in configfilelist.items():
	fl, fb = f.split('/')[-2:]
	if fl == 'cfglib':
		try:
			mt = os.path.getmtime(cfgdirserver + fb)
			mts = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')
		except Exception as E:
			mts = 'None'
			print('Error getting current library timestamp {}'.format(E))
	else:
		try:
			mt = os.path.getmtime(confserver + fb)
			mts = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')
		except Exception as E:
			mts = 'None'
			print('Error getting current base timestamp {}'.format(E))

	print('{} of {} vs {} ({})'.format(f,datetime.datetime.fromtimestamp(ftime).strftime('%Y-%m-%d %H:%M:%S'),mts,mt-ftime))
'''
debug.InitFlags(ParsedConfigFile)
isy.GetHandledNodeTypes(ParsedConfigFile)

for nm, val in config.sysvals.items():
	config.sysStore.SetVal([nm], val[0](ParsedConfigFile.get(nm, val[1])))
	if val[2] is not None: config.sysStore.AddAlert(nm, val[2])
screen.InitScreenParams(ParsedConfigFile)

screens.ScaleScreensInfo()

logsupport.Logs.Log("Parsed globals")
logsupport.Logs.Log("Switching to real log")
logsupport.Logs = logsupport.InitLogs(hw.screen, os.path.dirname(config.sysStore.configfile))
utilities.Logs = logsupport.Logs
tracebackplus.enable(file=logsupport.Stream_to_Logger)
logsupport.Logs.Log(u"Soft Home Automation Console")

logsupport.Logs.Log(u"  \u00A9 Kevin Kahn 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023")
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
logsupport.Logs.Log("Screen type: {}".format(hw.screentype))
if displayupdate.softrotate != 0:
	logsupport.Logs.Log(
		"Software rotation by {} degrees cw".format(displayupdate.rotationangle[displayupdate.softrotate]))
logsupport.Logs.Log(
	'(Display device: {} Driver: {} Dim Method: {})'.format(os.environ['SDL_FBDEV'], os.environ['SDL_VIDEODRIVER'],
															hw.DimType))
logsupport.Logs.Log("Touch controller: {}".format(utilities.ts.controller))
logsupport.Logs.Log(
	"(Capacitive: {} Shifts: x: {} y: {} Flips: x: {} y: {} Scale: x: {} y: {} swapaxes: {})".format(
		*utilities.ts.DumpTouchParams()))
logsupport.Logs.Log("Screen Orientation: ", ("Landscape", "Portrait")[displayupdate.portrait])
if config.sysStore.PersonalSystem:
	logsupport.Logs.Log("Personal System")
	logsupport.Logs.Log("Latency Tolerance: {}".format(controlevents.LateTolerance))
if os.path.exists("../.freezeconfig"):
	logsupport.Logs.Log('Configuration frozed', severity=ConsoleWarning)
if utilities.previousup > 0:
	logsupport.Logs.Log("Previous Console Lifetime: ", str(datetime.timedelta(seconds=utilities.previousup)))
if utilities.lastup > 0:
	logsupport.Logs.Log("Console Last Running at: ", time.ctime(utilities.lastup))
	logsupport.Logs.Log("Previous Console Downtime: ",
						str(datetime.timedelta(seconds=(config.sysStore.ConsoleStartTime - utilities.lastup))))
try:
	localops.LogUp()
except AttributeError:
	pass

logsupport.Logs.Log("Main config file: ", config.sysStore.configfile,
					time.strftime(' %c', time.localtime(configfilelist[config.sysStore.configfile])))
logsupport.Logs.Log("Default config file library: ", cfglib)
logsupport.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	if configfilelist[f] == 0:
		logsupport.Logs.Log("  ", p, " No Such File", severity=ConsoleWarning)
	else:
		logsupport.Logs.Log("  ", p, time.strftime(' %c', time.localtime(configfilelist[f])))
logsupport.Logs.CopyEarly()
debug.LogDebugFlags()

config.sysStore.Loglevel = int(ParsedConfigFile.get('LogLevel', config.sysStore.LogLevel))
logsupport.Logs.Log("Log level: ", config.sysStore.LogLevel)

logsupport.Logs.Log("Screensize: " + str(hw.screenwidth) + " x " + str(hw.screenheight))
logsupport.Logs.Log(
	"Scaling ratio: " + "{0:.2f} W ".format(hw.dispratioW) + "{0:.2f} H".format(hw.dispratioH))
if displayscreen.NewMouse:
	logsupport.Logs.Log('Using new touchscreen code')
else:
	logsupport.Logs.Log('Using old touchscreen code')

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
		# add stype Choice,  save all subsections, SCREEN names where to insert, then after specials do the insertions? todo
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
			stype_vers = stype.split('.')
			stype_base = stype_vers[0]
			hubvers = 0 if len(stype_vers) == 1 else int(stype_vers[1])
			if hubtyp == 'ISYDummy': hubvers = -1
			from hubs.hubs import HubInitError
			if stype_base == hubtyp:
				# noinspection PyBroadException
				try:
					logsupport.Logs.Log('Create {} hub version {} as {}'.format(stype_base, hubvers, i))
					hubs.hubs.Hubs[i] = pkg(i, v.get('address', ''), v.get('user', ''), v.get('password', ''), hubvers)
				except HubInitError:
					logsupport.Logs.Log("Hub {} could not initialize".format(i), severity=ConsoleError, tb=False)
					hubs.hubs.Hubs[i] = hubs.hubs.hubtypes['*missing*'](i, 'none', 'none', 'none', 0)
				# exitutils.Exit(exitutils.ERRORRESTART, immediate=True)  # retry - hub may be slow initializing
				except BaseException as e:
					logsupport.Logs.Log("Fatal console error - fix config file: ", e, severity=ConsoleError, tb=False)
					tbinfo = traceback.format_exc().splitlines()
					for l in tbinfo:
						logsupport.Logs.Log(l)
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
					skipfcst = int(v.get('skipforecast', 2))  # default is skip 2 cycles between forecast fetches
					units = str(v.get('units', 'I'))  # set to I for Imperial; M for Metric
					ws = info[0](desc, loccode, info[1], units)
					valuestore.NewValueStore(genericweatherstore.WeatherVals(desc, ws, refresh, skipfcst))
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
		nm = list(hubs.hubs.Hubs.keys())[0]
		logsupport.Logs.Log("No default Hub specified, using {}".format(nm), severity=ConsoleWarning)
		hubs.hubs.defaulthub = hubs.hubs.Hubs[nm]
else:
	try:
		nm = screen.screenStore.GetVal('DefaultHub')
		hubs.hubs.defaulthub = hubs.hubs.Hubs[nm]
		logsupport.Logs.Log("Default hub is: ", nm)
	except KeyError:
		logsupport.Logs.Log("Specified default Hub {} doesn't exist; hubs are: {}".format(
			screen.screenStore.GetVal('DefaultHub'), list(hubs.hubs.Hubs.keys())), severity=ConsoleWarning)
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

try:
	"""
	Build the Hub(s) object structure and connect the configured screens to it
	"""
	configobjects.MyScreens(ParsedConfigFile)
	logsupport.Logs.Log("Linked config to Hubs")

	"""
	Build the alerts structures
	"""
	alerttasks.ParseAlerts(alertspec)

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
	if utilfuncs.isdevsystem:
		with open('/home/pi/Console/helpfile.txt', 'w') as hf:
			print('System Parameters', file=hf)
			print('-----------------', file=hf)
			for I, v in config.sysvals.items():
				print('  {} (default: {})'.format(I, v[1]), file=hf)
			print(' ', file=hf)
			print('General Screen Parameters:', file=hf)
			print('--------------------------', file=hf)
			for I, v in screen.ScreenParams.items():
				print('  {} (default: {})'.format(I, v), file=hf)
			print(' ')
			print('Key Parameters:', file=hf)
			print('---------------', file=hf)
			for I, params in config.ItemTypes.items():
				if I in ('SliderScreen', 'ManualKeyDesc', 'VerifyScreen', 'ListChooserSubScreen', 'PagedDisplay',
						 'StatusDisplayScreen',
						 'ShowVersScreen', 'MaintScreenDesc', 'ScreenDesc'): continue
				print('Key: {}'.format(I), file=hf)
				for n in params:
					print('     {}'.format(n), file=hf)
# utilities.DumpDocumentation()
except Exception as E:
	logsupport.Logs.Log('Fatal Error while starting: {}'.format(E), severity=ConsoleError, hb=True, tb=False)
	exitutils.EarlyAbort('Configuration Error')

	"""
Run the main console loop
	"""
for n in alerttasks.monitoredvars:  # make sure vars used in alerts are updated to starting values
	valuestore.GetVal(n)
gui = threading.Thread(name='GUI', target=displayscreen.MainControlLoop)
config.ecode = 99
gui.start()

gui.join()
logsupport.Logs.Log("Main line exit: ", config.ecode)
timers.ShutTimers(config.terminationreason)
logsupport.Logs.Log('Console exiting')
config.Exiting = True
hw.GoBright(100)
pg.quit()
logsupport.DevPrint('Exit handling done')

sys.exit(config.ecode)