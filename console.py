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
from  multiprocessing import Process, Queue

from configobj import ConfigObj
import alerttasks
import config
import configobjects
import displayscreen
import globalparams
import isy
import logsupport
import maintscreen
import utilities
import requests
import urllib3
import json

urllib3.disable_warnings()
# import urllib3.contrib.pyopenssl

# sys.stdout = open('/home/pi/master.log', 'a', 0)
print time.strftime('%m-%d-%y %H:%M:%S'), 'CONSOLE START'
#urllib3.contrib.pyopenssl.inject_into_urllib3()

signal.signal(signal.SIGTERM, utilities.signal_handler)
signal.signal(signal.SIGINT, utilities.signal_handler)
signal.signal(signal.SIGCHLD, utilities.daemon_died)  # todo win alternative?

utilities.InitializeEnvironment()

config.exdir = os.path.dirname(os.path.abspath(__file__))
print 'Console start: ', config.exdir,
lastfn = ""
lastmod = 0
config.Console_pid = os.getpid()
for root, dirs, files in os.walk(config.exdir):
	for file in files:
		if file.endswith(".py"):
			fn = os.path.join(root, file)
			if os.path.getmtime(fn) > lastmod:
				lastmod = os.path.getmtime(fn)
				lastfn = fn
print 'Version (', lastfn, time.ctime(lastmod),

try:
	with open(config.exdir + '/' + 'versioninfo') as f:
		vn = f.readline()[:-1]
		vs = f.readline()[:-1]
		vi = f.readline()[:-1]
		print vn, vs, vi, ')'
except:
	vn = 'none'
	vs = 'none'
	vi = 'none'
	print 'No version info)'

import watchdaemon
from config import debugPrint

"""
Dynamically load class definitions for all defined screen types and link them to how configuration happens
"""
for screentype in os.listdir(os.path.dirname(os.path.abspath(sys.argv[0])) + '/screens'):
	if '__' not in screentype:
		splitname = os.path.splitext(screentype)
		if splitname[1] == '.py':
			importlib.import_module('screens.' + splitname[0])

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
includes = config.ParsedConfigFile.get('include', [])
while includes <> []:
	f = includes.pop(0)
	if f[0] <> '/':
		pfiles.append('+' + f)
		f = configdir + "/" + f
	else:
		pfiles.append(f)
	cfiles.append(f)
	tmpconf = ConfigObj(f)
	cfiles.append(f)
	includes = includes + tmpconf.get('include', [])
	config.ParsedConfigFile.merge(tmpconf)
	config.configfilelist[f] = os.path.getmtime(f)

config.Flags = logsupport.Flags()
utilities.ParseParam(globalparams)  # add global parameters to config file

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))
config.Logs.Log(u"Soft ISY Console")
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Version Information:")
config.Logs.Log(" Run from: ", config.exdir)
config.Logs.Log(" Last mod: ", lastfn)
config.Logs.Log(" Mod at: ", time.ctime(lastmod))
config.Logs.Log(" Tag: ", vn)
config.Logs.Log(" Sha: ", vs)
config.Logs.Log(" How: ", vi)
config.Logs.Log("Start time: ", time.strftime('%c'))
config.Logs.Log("Console Starting  pid: ", config.Console_pid)
config.Logs.Log("Main config file: ", config.configfile,
				time.strftime(' %c', time.localtime(config.configfilelist[config.configfile])))
config.Logs.Log("Including config files:")
for p, f in zip(pfiles, cfiles):
	config.Logs.Log("  ", p, time.strftime(' %c', time.localtime(config.configfilelist[f])))
for flg, fval in config.Flags.iteritems():
	if fval:
		config.Logs.Log('Debug flag ', flg, '=', fval, severity=logsupport.ConsoleWarning)

config.DS = displayscreen.DisplayScreen()  # create the actual device screen and touch manager

utilities.LogParams()
if 'Alerts' in config.ParsedConfigFile:
	alertspec = config.ParsedConfigFile['Alerts']
	del config.ParsedConfigFile['Alerts']
else:
	alertspec = None

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
configobjects.MyScreens()
config.Logs.Log("Linked config to ISY")

"""
Build the alerts structures
"""
alerttasks.Alerts(alertspec)
config.Logs.Log("Alerts established")

"""
Set up the watcher daemon and its communications
"""
config.toDaemon = Queue(300)
config.fromDaemon = Queue(300)
p = Process(target=watchdaemon.Watcher, name="Watcher")
p.daemon = True
p.start()
config.DaemonProcess = p
config.Daemon_pid = p.pid
debugPrint('Main', "Spawned watcher as: ", config.Daemon_pid)
config.Logs.Log("Watcher pid: " + str(config.Daemon_pid))

config.Logs.livelog = False  # turn off logging to the screen and give user a moment to scan
time.sleep(2)
# config.backlight.ChangeDutyCycle(config.BrightLevel)

"""
Set up the Maintenance Screen
"""
config.Logs.Log("Built Maintenance Screen")
maintscreen.SetUpMaintScreens()

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

	# humidity, temperature = Adafruit_DHT.read_retry(22,4)
	# tempF = temperature*9/5.0 +32
	# if humidity is not None and temperature is not None:
	#	print 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(tempF, humidity)


# todo - should return from the control loop mean anything?
