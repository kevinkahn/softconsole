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

import os
import signal
import sys
import time
import importlib
from  multiprocessing import Process, Queue

import requests
from configobj import ConfigObj

import config
import configobjects
import displayscreen
import globalparams
import isy
import logsupport
import utilities
import watchdaemon
from config import debugprint

import maintscreen


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

utilities.InitializeEnvironment()

if len(sys.argv) == 2:
    config.configfile = sys.argv[1]

config.Logs = logsupport.Logs(config.screen, os.path.dirname(config.configfile))

signal.signal(signal.SIGTERM, utilities.signal_handler)
signal.signal(signal.SIGINT, utilities.signal_handler)
signal.signal(signal.SIGCHLD, utilities.daemon_died)

config.ParsedConfigFile = ConfigObj(config.configfile)  # read the config.txt file

config.Logs.Log(u"Soft ISY Console")
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Start time: " + time.strftime('%c'))
config.Logs.Log("Console Starting  pid:" + str(os.getpid()))
config.Logs.Log("Config file: " + config.configfile)

config.DS = displayscreen.DisplayScreen()  # create the screens and touch manager

utilities.ParseParam(globalparams)  # add global parameters to config file

# Set up for ISY access
config.ISYprefix = 'http://' + config.ISYaddr + '/rest/'
config.ISYrequestsession = requests.session()
config.ISYrequestsession.auth = (config.ISYuser, config.ISYpassword)

# Build the ISY object structure
config.ISY = isy.ISY(config.ISYrequestsession)

config.Logs.Log("Enumerated ISY Structure")

configobjects.MyScreens()  # connect the screen structure with the ISY structure

"""
Set up the Maintenance Screen
"""
config.Logs.Log("Built Maintenance Screen")
config.MaintScreen = maintscreen.MaintScreenDesc()

"""
Set up the watcher daemon and its communitcations
"""
config.toDaemon = Queue()
config.fromDaemon = Queue()
p = Process(target=watchdaemon.Watcher, name="Watcher")
p.daemon = True
p.start()
config.DaemonProcess = p
debugprint(config.dbgMain, "Spawned watcher as: ", p.pid)
config.Logs.Log("Watcher pid: " + str(p.pid))

config.Logs.livelog = False  # turn off logging to the screen and give user a moment to scan
time.sleep(2)
config.backlight.ChangeDutyCycle(config.BrightLevel)
"""
Loop here using screen type to choose renderer and names to fill in cmdtxt - return value is next screen or a tap count
"""
config.CurrentScreen = config.HomeScreen
prevscreen = None
mainchainactive = True
paramsdoc = open('params.txt', 'w')
os.chmod('params.txt', 0o555)
paramsdoc.write('Global Parameters:\n')
for p in utilities.globdoc:
    paramsdoc.write('    ' + p + ' type: ' + utilities.globdoc[p].__name__ + '\n')
paramsdoc.write('Module Parameters:\n')
for p in utilities.moddoc:
    paramsdoc.write('    ' + p + '\n')
    paramsdoc.write('        Local Parameters:\n')
    for q in utilities.moddoc[p]['loc']:
        paramsdoc.write('            ' + q + ' type: ' + utilities.moddoc[p]['loc'][q].__name__ + '\n')
    paramsdoc.write('        Overrideable Globals:\n')
    for q in utilities.moddoc[p]['ovrd']:
        paramsdoc.write('            ' + q + '\n')
paramsdoc.close()


while 1:
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
    prevscreen = config.CurrentScreen
    config.CurrentScreen = nextscreen
