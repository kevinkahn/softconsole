"""
Copyright 2016 Kevin Kahn

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
import importlib
import os
import sys
import signal
import time
import cgitb
import datetime

from configobj import ConfigObj, Section
import isyeventmonitor

import config
import configobjects
import debug
import displayscreen
import globalparams
import isy
import logsupport
import maintscreen
import utilities
import requests
from logsupport import ConsoleWarning

import json


def handler(signum, frame):
	if signum == signal.SIGTERM:
		config.Logs.Log("Console received a SIGTERM - Exiting")
		time.sleep(1)
		os._exit(0)
	else:
		config.Logs.Log("Console received signal " + str(signum) + " Ignoring")


signal.signal(signal.SIGTERM, handler)

sectionget = Section.get


def CO_get(self, key, default):
	rtn = sectionget(self, key, default)
	if key in self:
		del self[key]
	return rtn


Section.get = CO_get


def LogBadParams(section, name):
	for nm, s in section.iteritems():
		if isinstance(s, Section):
			LogBadParams(s, nm)
		else:
			config.Logs.Log("Bad (unused) parameter name in: ", name, " (", nm, "=", str(s), ")",
							severity=ConsoleWarning)


config.exdir = os.path.dirname(os.path.abspath(__file__))
config.homedir = os.path.dirname(config.exdir)

earlylog = open(config.homedir + '/Console/earlylog.log', 'w', 0)
earlylog.write("Console start at " + time.strftime('%m-%d-%y %H:%M:%S') + '\n')

if os.getegid() <> 0:
	# Not running as root
	earlylog.write("Not running as root - exit\n")
	print "Must run as root"
	exit(999)

utilities.InitializeEnvironment()

earlylog.write('Environment initialized\n')


lastfn = ""
lastmod = 0
config.Console_pid = os.getpid()

earlylog.write('Exdir: ' + config.exdir + '  Pid: ' + str(config.Console_pid) + '\n')

for root, dirs, files in os.walk(config.exdir):
	for fname in files:
		if fname.endswith(".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn

try:
	with open(config.exdir + '/' + 'versioninfo') as f:
		config.versionname = f.readline()[:-1]
		config.versionsha = f.readline()[:-1]
		config.versiondnld = f.readline()[:-1]
		config.versioncommit = f.readline()[:-1]
except:
	config.versionname = 'none'
	config.versionsha = 'none'
	config.versiondnld = 'none'
	config.versioncommit = 'none'

earlylog.write(
	'Version/Sha/Dnld/Commit: ' + config.versionname + ' ' + config.versionsha + ' ' + config.versiondnld + ' ' + config.versioncommit + '\n')

"""
Dynamically load class definitions for all defined screen types and link them to how configuration happens
"""
for screentype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

earlylog.write("Screen types imported \n")

for alertproctype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/alerts'):
	if '__' not in alertproctype:
		splitname = os.path.splitext(alertproctype)
		if splitname[1] == '.py':
			importlib.import_module('alerts.' + splitname[0])

earlylog.write("Alert Proc types imported\n")

for n in config.alertprocs:
	config.alertprocs[n] = config.alertprocs[n]()  # instantiate an instance of each alert class

earlylog.write("Alert classes instantiated\n")

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

if not os.path.isfile(config.configfile):
	earlylog.write("Abort - no configuratio file\n")
	utilities.EarlyAbort('No Configuration File')

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file

earlylog.write("Parsed base config file\n")

configdir = os.path.dirname(config.configfile)

config.configfilelist[config.configfile] = os.path.getmtime(config.configfile)

cfiles = []
pfiles = []
cfglib = config.ParsedConfigFile.get('cfglib', '')
if cfglib <> '':
	cfglib += '/'
includes = config.ParsedConfigFile.get('include', [])
while includes:
	f = includes.pop(0)
	if f[0] <> '/':
		pfiles.append('+' + f)
		f = configdir + "/" + cfglib + f
	else:
		pfiles.append(f)
	cfiles.append(f)
	tmpconf = ConfigObj(f)
	includes = includes + tmpconf.get('include', [])
	config.ParsedConfigFile.merge(tmpconf)
	earlylog.write("Merged config file " + f + "\n")
	config.configfilelist[f] = os.path.getmtime(f)

debug.Flags = debug.InitFlags()

utilities.ParseParam(globalparams)  # add global parameters to config file

earlylog.write("Parsed globals\n")

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))
cgitb.enable(format='text')
config.Logs.Log(u"Soft ISY Console")
earlylog.write("Switched to real log\n")
earlylog.close()
# TODO delete the early log
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016, 2017")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Version Information:")
config.Logs.Log(" Run from: ", config.exdir)
config.Logs.Log(" Last mod: ", lastfn)
config.Logs.Log(" Mod at: ", time.ctime(lastmod))
config.Logs.Log(" Tag: ", config.versionname)
config.Logs.Log(" Sha: ", config.versionsha)
config.Logs.Log(" How: ", config.versiondnld)
config.Logs.Log(" Version date: ", config.versioncommit)
config.Logs.Log("Start time: ", time.ctime(config.starttime))
with open(config.homedir + "/.ConsoleStart", "w") as f:
	f.write(str(config.starttime) + '\n')
config.Logs.Log("Console Starting  pid: ", config.Console_pid)
config.Logs.Log("Host name: ", config.hostname)
config.Logs.Log("Screen type: ", config.screentype)
config.Logs.Log("Screen Orientation: ", ("Landscape", "Portrait")[config.portrait])
if config.personalsystem:
	config.Logs.Log("Personal System")
if config.previousup > 0:
	config.Logs.Log("Previous Console Lifetime: ", str(datetime.timedelta(seconds=config.previousup)))
if config.lastup > 0:
	config.Logs.Log("Previous Console Downtime: ", str(datetime.timedelta(seconds=(config.starttime - config.lastup))))
config.Logs.Log("Main config file: ", config.configfile,
				time.strftime(' %c', time.localtime(config.configfilelist[config.configfile])))
config.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	config.Logs.Log("  ", p, time.strftime(' %c', time.localtime(config.starttime - config.configfilelist[f])))
for flg, fval in debug.Flags.iteritems():
	if fval:
		config.Logs.Log('Debug flag ', flg, '=', fval, severity=logsupport.ConsoleWarning)
		config.LogLevel = 0  # if a debug flag is set force Logging unless explicitly overridden
config.LogLevel = int(config.ParsedConfigFile.get('LogLevel', config.LogLevel))
config.Logs.Log("Log level: ", config.LogLevel)
config.DS = displayscreen.DisplayScreen()  # create the actual device screen and touch manager

utilities.LogParams()


"""
Set up for ISY access
"""
config.ISYprefix = 'http://' + config.ISYaddr + '/rest/'
config.ISYrequestsession = requests.session()
config.ISYrequestsession.auth = (config.ISYuser, config.ISYpassword)

config.ISY = isy.ISY(config.ISYrequestsession)
config.Logs.Log("Enumerated ISY Structure")


"""
Build the ISY object structure and connect the configured screens to it
"""
import alerttasks

cmdvar = 'Command.' + config.hostname.replace('-', '.')
if cmdvar in config.ISY.varsInt:
	tmp = ConfigObj()
	tmp['RemoteCommands2'] = {'Type': 'IntVarChange', 'Var': cmdvar, 'Test': 'NE', 'Value': '0',
							  'Invoke': 'NetCmd.Command'}
else:
	tmp = None

if 'Alerts' in config.ParsedConfigFile:
	alertspec = config.ParsedConfigFile['Alerts']
	if tmp <> None:
		alertspec.merge(tmp)
	del config.ParsedConfigFile['Alerts']
else:
	if tmp <> None:
		alertspec = ConfigObj()
		alertspec.merge(tmp)
	else:
		alertspec = None

if 'Variables' in config.ParsedConfigFile:
	i = 0
	for nm, val in config.ParsedConfigFile['Variables'].iteritems():
		config.ISY.LocalVars.append(int(val))
		config.ISY.varsLocal[nm] = i
		config.ISY.varsLocalInv[i] = nm
		config.Logs.Log("Local variable: " + nm + "(" + str(i) + ") = " + str(val))
		i += 1
	del config.ParsedConfigFile['Variables']
configobjects.MyScreens()
config.Logs.Log("Linked config to ISY")

"""
Set up the websocket thread to handle ISY stream
"""
isyeventmonitor.CreateWSThread()

"""
Build the alerts structures
"""
config.Alerts = alerttasks.Alerts(alertspec)
config.Logs.Log("Alerts established")

"""
Set up the Maintenance Screen
"""
config.Logs.Log("Built Maintenance Screen")
maintscreen.SetUpMaintScreens()

config.Logs.livelog = False  # turn off logging to the screen and give user a moment to scan
time.sleep(2)

LogBadParams(config.ParsedConfigFile, "Globals")
LogBadParams(alertspec, "Alerts")
"""
Dump documentation
"""
utilities.DumpDocumentation()

docfile = open('confignew.txt', 'w')
config.ParsedConfigFile.write(docfile)
docfile.close()

"""
Run the main console loop
"""
config.DS.MainControlLoop(config.HomeScreen)

# This never returns

	# humidity, temperature = Adafruit_DHT.read_retry(22,4)
	# tempF = temperature*9/5.0 +32
	# if humidity is not None and temperature is not None:
	#	print 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(tempF, humidity)

