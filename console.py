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
import debug
import config
import importlib
import os
import sys
import signal
import time
import cgitb
import datetime
import pygame

# noinspection PyProtectedMember
from configobj import ConfigObj, Section
import isyeventmonitor


import configobjects
import exitutils

import displayscreen
import globalparams
import isy
import logsupport
import maintscreen
import utilities
import requests
from logsupport import ConsoleWarning
import weatherfromatting
from stores import mqttsupport, valuestore, localvarsupport

import json


def handler(signum, frame):
	if signum in (signal.SIGTERM, signal.SIGINT):
		logsupport.Logs.Log("Console received a termination signal ", str(signum), " - Exiting")
		time.sleep(1)
		pygame.display.quit()
		pygame.quit()
		os._exit(0)
	else:
		logsupport.Logs.Log("Console received signal " + str(signum) + " Ignoring")


signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)


config.Console_pid = os.getpid()
config.exdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(config.exdir)  # make sure we are in the directory we are executing from
config.homedir = os.path.dirname(config.exdir)
logsupport.Logs.Log("Console (" + str(config.Console_pid) + ") starting in "+os.getcwd())

sectionget = Section.get
def CO_get(self, key, default, delkey=True):
	rtn = sectionget(self, key, default)
	if key in self and delkey:
		del self[key]
	return rtn
Section.get = CO_get


def LogBadParams(section, name):
	for nm, s in section.iteritems():
		if isinstance(s, Section):
			LogBadParams(s, nm)
		else:
			logsupport.Logs.Log("Bad (unused) parameter name in: ", name, " (", nm, "=", str(s), ")",
							severity=ConsoleWarning)

if os.getegid() <> 0:
	# Not running as root
	logsupport.Logs.Log("Not running as root - exit")
	print ("Must run as root")
	os._exit(exitutils.EARLYABORT)

utilities.InitializeEnvironment()

logsupport.Logs.Log('Environment initialized on host '+ config.hostname)

lastfn = ""
lastmod = 0
config.Console_pid = os.getpid()

logsupport.Logs.Log('Exdir: ' + config.exdir + '  Pid: ' + str(config.Console_pid))

for root, dirs, files in os.walk(config.exdir):
	for fname in files:
		if fname.endswith(".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn

try:
	with open(config.exdir + '/' + 'versioninfo') as f:
		config.versionname = f.readline()[:-1].rstrip()
		config.versionsha = f.readline()[:-1].rstrip()
		config.versiondnld = f.readline()[:-1].rstrip()
		config.versioncommit = f.readline()[:-1].rstrip()
except:
	config.versionname = 'none'
	config.versionsha = 'none'
	config.versiondnld = 'none'
	config.versioncommit = 'none'

logsupport.Logs.Log(
	'Version/Sha/Dnld/Commit: ' + config.versionname + ' ' + config.versionsha + ' ' + config.versiondnld + ' ' + config.versioncommit)

"""
Dynamically load class definitions for all defined screen types and link them to how configuration happens
"""
#for screentype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/screens'):
for screentype in os.listdir(os.getcwd() + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

logsupport.Logs.Log("Screen types imported")

#for alertproctype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/alerts'):
for alertproctype in os.listdir(os.getcwd() + '/alerts'):
	if '__' not in alertproctype:
		splitname = os.path.splitext(alertproctype)
		if splitname[1] == '.py':
			importlib.import_module('alerts.' + splitname[0])

logsupport.Logs.Log("Alert Proc types imported")

for n in config.alertprocs:
	config.alertprocs[n] = config.alertprocs[n]()  # instantiate an instance of each alert class

logsupport.Logs.Log("Alert classes instantiated")

"""
Initialize the Console
"""

with open(config.exdir + '/termshortenlist', 'r') as f:
	try:
		config.TermShortener = json.load(f)
	except:
		config.TermShortener = {}

if len(sys.argv) == 2:
	config.configfile = sys.argv[1]
elif os.path.isfile(config.configfilebase + "config.txt"):
	config.configfile = config.configfilebase + "config.txt"
else:
	config.configfile = config.configfilebase + "config-" + config.hostname + ".txt"

logsupport.Logs.Log("Configuration file: " + config.configfile)

if not os.path.isfile(config.configfile):
	print ("Abort - no configuration file found")
	logsupport.Logs.Log('Abort - no configuration file ('+config.hostname+')')
	exitutils.EarlyAbort('No Configuration File (' + config.hostname + ')')

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file

logsupport.Logs.Log("Parsed base config file")

configdir = os.path.dirname(config.configfile)

config.configfilelist[config.configfile] = os.path.getmtime(config.configfile)

cfiles = []
pfiles = []
cfglib = config.ParsedConfigFile.get('cfglib', '')
if cfglib <> '':
	cfglib += '/'
if cfglib[0] <> '/':
	cfglib = configdir + '/' + cfglib
includes = config.ParsedConfigFile.get('include', [])
while includes:
	f = includes.pop(0)
	if f[0] <> '/':
		pfiles.append('+' + f)
		f = cfglib + f
	else:
		pfiles.append(f)
	cfiles.append(f)
	tmpconf = ConfigObj(f)
	includes = includes + tmpconf.get('include', [])
	config.ParsedConfigFile.merge(tmpconf)
	logsupport.Logs.Log("Merged config file " + f)
	try:
		config.configfilelist[f] = os.path.getmtime(f)
	except:
		logsupport.Logs.Log("MISSING config file " + f)
		config.configfilelist[f] = 0

debug.InitFlags(config.ParsedConfigFile)

utilities.ParseParam(globalparams)  # add global parameters to config file

# preload weather icon cache for some common terms
for cond in ('clear','cloudy','mostlycloudy','mostlysunny','partlycloudy','partlysunny','rain','snow','sunny','chancerain'):
	try:
		weatherfromatting.get_icon('https://icons.wxug.com/i/c/k/' + cond + '.gif')
	except:
		pass

logsupport.Logs.Log("Parsed globals")
logsupport.Logs.Log("Switching to real log")
logsupport.Logs = logsupport.InitLogs(config.screen, os.path.dirname(config.configfile))
cgitb.enable(format='text')
logsupport.Logs.Log(u"Soft ISY Console")

logsupport.Logs.Log(u"  \u00A9 Kevin Kahn 2016, 2017")
logsupport.Logs.Log("Software under Apache 2.0 License")
logsupport.Logs.Log("Version Information:")
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
	logsupport.Logs.Log("Previous Console Downtime: ", str(datetime.timedelta(seconds=(config.starttime - config.lastup))))
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

"""
Pull out non-screen sections
"""
for i,v in config.ParsedConfigFile.iteritems():
	if isinstance(v, Section):
		stype = v.get('type',None,delkey=False)
		if stype == 'MQTT':
			"""
			Set up mqtt brokers
			"""
			valuestore.NewValueStore(mqttsupport.MQTTBroker(i, v))
			del config.ParsedConfigFile[i]
		elif stype == "Locals":
			valuestore.NewValueStore(localvarsupport.LocalVars(i, v))
			del config.ParsedConfigFile[i]

	"""
	Eventually add HA and ISY sections  TODO
	"""

import alerttasks

"""
Set up for ISY access
"""
if config.ISYaddr != '':
	if config.ISYaddr.startswith( 'http' ) :
	  config.ISYprefix = config.ISYaddr + '/rest/'
	else:
	  config.ISYprefix = 'http://' + config.ISYaddr + '/rest/'
	config.ISYrequestsession = requests.session()
	config.ISYrequestsession.auth = (config.ISYuser, config.ISYpassword)

	config.ISY = isy.ISY(config.ISYrequestsession)
	logsupport.Logs.Log("Enumerated ISY Structure")
	# todo seems odd that the following code is here and has to be skipped for null ISY case - should be in the ISY definition
	cmdvar = valuestore.InternalizeVarName('ISY:Int:Command.' + config.hostname.replace('-', '.'))
	alertspeclist = None
	for k in valuestore.ValueStores['ISY'].items():
		if k == tuple(cmdvar[1:]):
			alertspeclist = ConfigObj()
			alertspeclist['RemoteCommands2'] = {
				'Type': 'VarChange', 'Var': valuestore.ExternalizeVarName(cmdvar), 'Test': 'NE', 'Value': '0',
				'Invoke': 'NetCmd.Command'}
			break

else:
	config.ISY = isy.ISY(None)
	alertspeclist = None # todo see comment above
	logsupport.Logs.Log("No ISY Specified", severity=ConsoleWarning)

"""
Set up alerts
"""
if 'Alerts' in config.ParsedConfigFile:
	alertspec = config.ParsedConfigFile['Alerts']
	if alertspeclist is not None:
		alertspec.merge(alertspeclist)
	del config.ParsedConfigFile['Alerts']
else:
	alertspec = ConfigObj()
	if alertspeclist is not None:
		alertspec.merge(alertspeclist)

"""
Build the ISY object structure and connect the configured screens to it
"""

if 'Variables' in config.ParsedConfigFile:
	valuestore.NewValueStore(localvarsupport.LocalVars('LocalVars',config.ParsedConfigFile['Variables']))
	i = 0
	tn = ['LocalVars','']
	for nm, val in config.ParsedConfigFile['Variables'].iteritems():
		logsupport.Logs.Log("Local variable: " + nm + "(" + str(i) + ") = " + str(val))
		tn[1] = nm
		valuestore.SetVal(tn, val)
		valuestore.SetAttr(tn, (3, i))
		i += 1
	del config.ParsedConfigFile['Variables']
configobjects.MyScreens()
logsupport.Logs.Log("Linked config to ISY")


"""
Set up the websocket thread to handle ISY stream
"""
isyeventmonitor.CreateWSThread()

"""
Build the alerts structures
"""
config.Alerts = alerttasks.Alerts(alertspec)
logsupport.Logs.Log("Alerts established")

"""
Set up the Maintenance Screen
"""
logsupport.Logs.Log("Built Maintenance Screen")
maintscreen.SetUpMaintScreens()

logsupport.Logs.livelog = False  # turn off logging to the screen and give user a moment to scan
time.sleep(2)

LogBadParams(config.ParsedConfigFile, "Globals")
LogBadParams(alertspec, "Alerts")
"""
Dump documentation if development version
"""
if config.versionname == 'development':
	utilities.DumpDocumentation()

"""
Run the main console loop
"""
valuestore.ValueStores['ISY'].CheckValsUpToDate()
config.DS.MainControlLoop(config.HomeScreen)
logsupport.Logs.Log("Main line exit: ",config.ecode)
pygame.quit()
os._exit(config.ecode)

# This never returns


