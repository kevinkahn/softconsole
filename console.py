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
# import Adafruit_DHT
import importlib
import os
import signal
import sys
import time
from  multiprocessing import Process, Queue

import requests
from configobj import ConfigObj

import config
import configobjects
import displayscreen
import globalparams
import isy
import logsupport
import maintscreen
import screen
import utilities
import requests
import urllib3

urllib3.disable_warnings()

import watchdaemon
from config import debugprint

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

# requests.packages.urllib3.disable_warnings(
#	InsecureRequestWarning)  # probably should fix certificates at some point todo

utilities.InitializeEnvironment()

if len(sys.argv) == 2:
	config.configfile = sys.argv[1]

signal.signal(signal.SIGTERM, utilities.signal_handler)
signal.signal(signal.SIGINT, utilities.signal_handler)
signal.signal(signal.SIGCHLD, utilities.daemon_died)  # todo win alternative?

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file
utilities.ParseParam(globalparams)  # add global parameters to config file

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))
config.Logs.Log(u"Soft ISY Console")
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Start time: ", time.strftime('%c'))
config.Logs.Log("Console Starting  pid: ", os.getpid())
config.Logs.Log("Config file: ", config.configfile)

config.DS = displayscreen.DisplayScreen()  # create the actual device screen and touch manager

utilities.LogParams()

"""
Set up for ISY access
"""
config.ISYprefix = 'https://' + config.ISYaddr + '/rest/'
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
Set up the watcher daemon and its communications
"""
config.toDaemon = Queue(300)
config.fromDaemon = Queue(300)
p = Process(target=watchdaemon.Watcher, name="Watcher")
p.daemon = True
p.start()
config.DaemonProcess = p
debugprint(config.dbgMain, "Spawned watcher as: ", p.pid)
config.Logs.Log("Watcher pid: " + str(p.pid))

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
config.CurrentScreen = config.HomeScreen
prevscreen = None
mainchainactive = True

while 1:
	# humidity, temperature = Adafruit_DHT.read_retry(22,4)
	# tempF = temperature*9/5.0 +32
	# if humidity is not None and temperature is not None:
	#	print 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(tempF, humidity)
	nextscreen = config.CurrentScreen.HandleScreen(prevscreen <> config.CurrentScreen)
	if isinstance(nextscreen, int):
		if nextscreen < 5:
			if mainchainactive:
				nextscreen = config.HomeScreen2
				mainchainactive = False
			else:
				nextscreen = config.HomeScreen
				mainchainactive = True
		else:
			nextscreen = config.MaintScreen
	elif nextscreen is None:
		nextscreen = config.HomeScreen
	elif not isinstance(nextscreen, screen.ScreenDesc):
		config.Logs.Log("Internal error unknown nextscreen", severity=logsupport.ConsoleError)
	prevscreen = config.CurrentScreen
	config.CurrentScreen = nextscreen
