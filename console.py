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
import signal
import sys
import time
import threading

from configobj import ConfigObj
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

import json

# urllib3.disable_warnings()
# import urllib3.contrib.pyopenssl

# sys.stdout = open('/home/pi/master.log', 'a', 0)
print time.strftime('%m-%d-%y %H:%M:%S'), 'CONSOLE START'
#urllib3.contrib.pyopenssl.inject_into_urllib3()

signal.signal(signal.SIGTERM, utilities.signal_handler)
signal.signal(signal.SIGINT, utilities.signal_handler)


utilities.InitializeEnvironment()

config.exdir = os.path.dirname(os.path.abspath(__file__))
print 'Console start: ', config.exdir,
lastfn = ""
lastmod = 0
config.Console_pid = os.getpid()
for root, dirs, files in os.walk(config.exdir):
	for fname in files:
		if fname.endswith(".py"):
			fn = os.path.join(root, fname)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn
print 'Version (', lastfn, time.ctime(lastmod),

try:
	with open(config.exdir + '/' + 'versioninfo') as f:
		config.versionname = f.readline()[:-1]
		config.versionsha = f.readline()[:-1]
		config.versiondnld = f.readline()[:-1]
		config.versioncommit = f.readline()[:-1]
		print config.versionname, config.versionsha, config.versiondnld, config.versioncommit, ')'
except:
	config.versionname = 'none'
	config.versionsha = 'none'
	config.versiondnld = 'none'
	config.versioncommit = 'none'
	print 'No version info)'


from debug import debugPrint

"""
Dynamically load class definitions for all defined screen types and link them to how configuration happens
"""
for screentype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

for alertproctype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/alerts'):
	if '__' not in alertproctype:
		splitname = os.path.splitext(alertproctype)
		if splitname[1] == '.py':
			importlib.import_module('alerts.' + splitname[0])
for n in config.alertprocs:
	config.alertprocs[n] = config.alertprocs[n]()  # instantiate an instance of each alert class

"""
Initialize the Console
"""

config.starttime = time.time()

with open(config.exdir + '/termshortenlist', 'r') as f:
	try:
		config.TermShortener = json.load(f)
	except:
		config.TermShortener = {}

if len(sys.argv) == 2:
	config.configfile = sys.argv[1]

if not os.path.isfile(config.configfile):
	utilities.EarlyAbort('No Configuration File')



config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file
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
	config.configfilelist[f] = os.path.getmtime(f)

debug.Flags = debug.InitFlags()
logsupport.LogLevel = int(config.ParsedConfigFile.get('LogLevel', 2))
utilities.ParseParam(globalparams)  # add global parameters to config file

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))
config.Logs.Log(u"Soft ISY Console")
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Version Information:")
config.Logs.Log(" Run from: ", config.exdir)
config.Logs.Log(" Last mod: ", lastfn)
config.Logs.Log(" Mod at: ", time.ctime(lastmod))
config.Logs.Log(" Tag: ", config.versionname)
config.Logs.Log(" Sha: ", config.versionsha)
config.Logs.Log(" How: ", config.versiondnld)
config.Logs.Log(" Version date: ", config.versioncommit)
config.Logs.Log("Start time: ", time.strftime('%c'))
config.Logs.Log("Console Starting  pid: ", config.Console_pid)
config.Logs.Log("Log level: ", config.LogLevel)
config.Logs.Log("Main config file: ", config.configfile,
				time.strftime(' %c', time.localtime(config.configfilelist[config.configfile])))
config.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	config.Logs.Log("  ", p, time.strftime(' %c', time.localtime(config.configfilelist[f])))
for flg, fval in debug.Flags.iteritems():
	if fval:
		config.Logs.Log('Debug flag ', flg, '=', fval, severity=logsupport.ConsoleWarning)

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

if 'Alerts' in config.ParsedConfigFile:
	alertspec = config.ParsedConfigFile['Alerts']
	del config.ParsedConfigFile['Alerts']
else:
	alertspec = None
configobjects.MyScreens()
config.Logs.Log("Linked config to ISY")

"""
Set up the websocket thread to handle ISY stream
"""
config.EventMonitor = isyeventmonitor.ISYEventMonitor()
config.QH = threading.Thread(name='QH', target=config.EventMonitor.QHandler)
config.QH.setDaemon(True)
config.QH.start()
config.Logs.Log("ISY stream thread started")

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

"""
Dump documentation
"""
utilities.DumpDocumentation()

docfile = open('confignew.txt', 'w')
config.ParsedConfigFile.write(docfile)
docfile.close()

"""
Loop here using screen type to choose renderer and names to fill in cmdtxt - return value is next screen or a tap count
"""
config.DS.MainControlLoop(config.HomeScreen)

# This never returns

	# humidity, temperature = Adafruit_DHT.read_retry(22,4)
	# tempF = temperature*9/5.0 +32
	# if humidity is not None and temperature is not None:
	#	print 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(tempF, humidity)

