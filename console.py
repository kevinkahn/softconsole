#!/usr/bin/python -u
# above assumes it points at python 2.7 and may not be portable
"""
Copyright 2016, 2017 Kevin Kahn

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
import pygame
import valuestore

# noinspection PyProtectedMember
from configobj import ConfigObj, Section
import isyeventmonitor

import config
import configobjects
import exitutils
import debug
import displayscreen
import globalparams
import isy
import logsupport
import maintscreen
import utilities
import requests
from logsupport import ConsoleWarning, ConsoleDetail
import weatherinfo
import mqttsupport
import localvarsupport

import json


def handler(signum, frame):
	if signum in (signal.SIGTERM, signal.SIGINT):
		config.Logs.Log("Console received a termination signal ", str(signum), " - Exiting")
		time.sleep(1)
		pygame.display.quit()
		pygame.quit()
		os._exit(0)
	else:
		config.Logs.Log("Console received signal " + str(signum) + " Ignoring")


signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

sectionget = Section.get

config.Console_pid = os.getpid()
config.exdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(config.exdir)  # make sure we are in the directory we are executing from
config.homedir = os.path.dirname(config.exdir)
print("Console (" + str(config.Console_pid) + ") starting in "+os.getcwd())

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
			config.Logs.Log("Bad (unused) parameter name in: ", name, " (", nm, "=", str(s), ")",
							severity=ConsoleWarning)

earlylog = open(config.homedir + '/Console/earlylog.log', 'w', 0)
earlylog.write("Console start at " + time.strftime('%m-%d-%y %H:%M:%S') + ' on ' + config.hostname + '\n')

if os.getegid() <> 0:
	# Not running as root
	earlylog.write("Not running as root - exit\n")
	print ("Must run as root")
	os._exit(exitutils.EARLYABORT)

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
		config.versionname = f.readline()[:-1].rstrip()
		config.versionsha = f.readline()[:-1].rstrip()
		config.versiondnld = f.readline()[:-1].rstrip()
		config.versioncommit = f.readline()[:-1].rstrip()
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
#for screentype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/screens'):
for screentype in os.listdir(os.getcwd() + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

earlylog.write("Screen types imported \n")

#for alertproctype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/alerts'):
for alertproctype in os.listdir(os.getcwd() + '/alerts'):
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

# preload weather icon cache for some common terms
for cond in ('clear','cloudy','mostlycloudy','mostlysunny','partlycloudy','partlysunny','rain','snow','sunny','chancerain'):
	try:
		weatherinfo.get_icon('https://icons.wxug.com/i/c/k/' + cond + '.gif')
	except:
		pass

if len(sys.argv) == 2:
	config.configfile = sys.argv[1]
elif os.path.isfile(config.configfilebase + "config.txt"):
	config.configfile = config.configfilebase + "config.txt"
else:
	config.configfile = config.configfilebase + "config-" + config.hostname + ".txt"

print ("Configuration file: " + config.configfile)

if not os.path.isfile(config.configfile):
	print ("Abort - no configuration file found")
	earlylog.write("Abort - no configuration file ('+config.hostname+')'\n")
	exitutils.EarlyAbort('No Configuration File (' + config.hostname + ')')

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file

earlylog.write("Parsed base config file\n")

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
	earlylog.write("Merged config file " + f + "\n")
	try:
		config.configfilelist[f] = os.path.getmtime(f)
	except:
		earlylog.write("MISSING config file " + f + "\n")
		config.configfilelist[f] = 0

debug.Flags = debug.InitFlags() # todo delete when switched to ValStore
valuestore.NewValueStore(localvarsupport.LocalVars('Debug',debug.DbgVars))

utilities.ParseParam(globalparams)  # add global parameters to config file

earlylog.write("Parsed globals\n")

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))
cgitb.enable(format='text')
config.Logs.Log(u"Soft ISY Console")
earlylog.write("Switched to real log\n")
earlylog.close()
os.remove(config.homedir + '/Console/earlylog.log')
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
	config.Logs.Log("Console Last Running at: ", time.ctime(config.lastup))
	config.Logs.Log("Previous Console Downtime: ", str(datetime.timedelta(seconds=(config.starttime - config.lastup))))
config.Logs.Log("Main config file: ", config.configfile,
				time.strftime(' %c', time.localtime(config.configfilelist[config.configfile])))
config.Logs.Log("Default config file library: ", cfglib)
config.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	if config.configfilelist[f] == 0:
		config.Logs.Log("  ", p, " No Such File", severity=ConsoleWarning)
	else:
		config.Logs.Log("  ", p, time.strftime(' %c', time.localtime(config.configfilelist[f])))
for flg, fval in debug.Flags.iteritems():
	if fval:
		config.Logs.Log('Debug flag ', flg, '=', fval, severity=logsupport.ConsoleWarning)
		config.LogLevel = 0  # if a debug flag is set force Logging unless explicitly overridden
config.LogLevel = int(config.ParsedConfigFile.get('LogLevel', config.LogLevel))
config.Logs.Log("Log level: ", config.LogLevel)
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
			valuestore.NewValueStore(localvarsupport.LocalVars(i,v))
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
	config.Logs.Log("Enumerated ISY Structure")
	# todo seems odd that the following code is here and has to be skipped for null ISY case - should be in the ISY definition
	cmdvar = 'Command.' + config.hostname.replace('-', '.')
	if cmdvar in config.ISY.varsInt:
		alertspeclist = ConfigObj()
		alertspeclist['RemoteCommands2'] = {
			'Type': 'IntVarChange', 'Var': cmdvar, 'Test': 'NE', 'Value': '0',
			'Invoke': 'NetCmd.Command'}
	else:
		alertspeclist = None
else:
	config.ISY = isy.ISY(None)
	alertspeclist = None # todo see comment above
	config.Logs.Log("No ISY Specified", severity=ConsoleWarning)

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
	i = 0
	for nm, val in config.ParsedConfigFile['Variables'].iteritems():
		config.ISY.LocalVars.append(int(val))
		config.ISY.varsLocal[nm] = i
		config.ISY.varsLocalInv[i] = nm
		config.Logs.Log("Local variable: " + nm + "(" + str(i) + ") = " + str(val))
		i += 1
#	localvarsupport.LocalVars('Local',config.ParsedConfigFile['Variables'])
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
Dump documentation if development version
"""
if config.versionname == 'development':
	utilities.DumpDocumentation()


"""
Run the main console loop
"""
config.DS.MainControlLoop(config.HomeScreen)
config.Logs.Log("Main line exit: ",config.ecode)
pygame.quit()
os._exit(config.ecode)

# This never returns


