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
import pygame
import signal
import sys
import time
from  multiprocessing import Process, Queue

import RPi.GPIO as GPIO
from configobj import ConfigObj
import requests

import configobjects
import displayscreen
import isy
import logsupport
import toucharea
import watchdaemon
import config
from config import debugprint

"""
The next import is functional in that it is what causes the screen types to be registered with the Console
"""
import clockscreen, keyscreen, thermostatscreen, weatherscreen, maintscreen


def signal_handler(sig, frame):
    print "Signal: {}".format(sig)
    print "pid: ", os.getpid()
    time.sleep(1)
    pygame.quit()
    print time.time(), "Console Exiting"
    sys.exit(0)


def daemon_died(sig, frame):
    print "CSignal: {}".format(sig)
    if config.DaemonProcess is None:
        return
    if config.DaemonProcess.is_alive():
        print "Child ok"
    else:
        print time.time(), "Daemon died!"
        pygame.quit()
        sys.exit()


def ParseAndLog(pname, default):
    val = config.ParsedConfigFile.get(pname, default)
    config.Logs.Log(pname + ": " + str(val))
    return val


"""
Actual Code to Drive Console
"""
config.starttime = time.time()

os.environ['SDL_FBDEV'] = '/dev/fb1'
os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
os.environ['SDL_MOUSEDRV'] = 'TSLIB'
os.environ['SDL_VIDEODRIVER'] = 'fbcon'

pygame.display.init()
pygame.font.init()
config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)
config.screen = pygame.display.set_mode((config.screenwidth, config.screenheight), pygame.FULLSCREEN)
config.screen.fill((0, 0, 0))  # clear screen
pygame.display.update()
pygame.mouse.set_visible(False)

if len(sys.argv) == 2:
    fn = sys.argv[1]
else:
    fn = "/home/pi/Console/config.txt"

config.Logs = logsupport.Logs(config.screen, os.path.dirname(fn))

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGCHLD, daemon_died)

config.ParsedConfigFile = ConfigObj(fn)

config.Logs.Log(u"Soft ISY Console")
config.Logs.Log(u"  \u00A9 Kevin Kahn 2016")
config.Logs.Log("Software under Apache 2.0 License")
config.Logs.Log("Start time: " + time.strftime('%c'))
config.Logs.Log("Console Starting  pid:" + str(os.getpid()))
config.Logs.Log("Config file: " + fn)
config.Logs.Log("Disk logfile:" + config.Logs.logfilename)

config.DS = displayscreen.DisplayScreen()

# Global settings from config file
config.ISYaddr = str(config.ParsedConfigFile.get('ISYaddr', ""))
config.ISYuser = str(config.ParsedConfigFile.get('ISYuser', ""))
config.ISYpassword = str(config.ParsedConfigFile.get('ISYpassword', ""))
config.HomeScreenName = str(ParseAndLog('HomeScreenName', ""))
config.HomeScreenTO = int(ParseAndLog('HomeScreenTO', config.HomeScreenTO))
config.DimLevel = int(ParseAndLog('DimLevel', config.DimLevel))
config.BrightLevel = int(ParseAndLog('BrightLevel', config.BrightLevel))
config.DimTO = int(ParseAndLog('DimTO', config.DimTO))
config.CmdKeyCol = str(ParseAndLog('CmKeyColor', config.CmdKeyCol))
config.CmdCharCol = str(ParseAndLog('CmdCharCol', config.CmdCharCol))
config.MultiTapTime = int(ParseAndLog('MultiTapTime', config.MultiTapTime))
config.DimHomeScreenCoverName = str(ParseAndLog('DimHomeScreenCoverName', ""))
config.DefaultCharColor = str(ParseAndLog('DefaultCharColor', config.DefaultCharColor))
config.DefaultBkgndColor = str(ParseAndLog('DefaultBkgndColor', config.DefaultBkgndColor))

config.MainChain = config.ParsedConfigFile.get('MainChain', [])
config.SecondaryChain = config.ParsedConfigFile.get('SecondaryChain', [])
config.ISYprefix = 'http://' + config.ISYaddr + '/rest/'

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
config.backlight = GPIO.PWM(18, 1024)
config.backlight.start(100)

config.ISYrequestsession = requests.session()
config.ISYrequestsession.auth = (config.ISYuser, config.ISYpassword)

config.ISY = isy.ISY(config.ISYrequestsession, config.ISYaddr)

# nodemgr = config.ISY.myisy.nodes
# programs = config.ISY.myisy.programs
# if config.ISY.myisy.connected:
#    Logs.Log("Connected to ISY: " + config.ISYaddr)
# else:
#    Logs.Log("Failed to connect to ISY", logsupport.Error)

# config.ISY.WalkFolder(nodemgr)
config.Logs.Log("Enumerated ISY Devices/Scenes")
# config.ISY.EnumeratePrograms(programs)
config.Logs.Log("Enumerated ISY Programs")

pygame.fastevent.init()
CurrentScreenInfo = configobjects.MyScreens()

"""
Set up the Maintenance Screen
"""
config.Logs.Log("Built Maintenance Screen")
config.MaintScreen = maintscreen.MaintScreenDesc()  # temp use of HS2

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

toucharea.InitButtonFonts()

config.Logs.livelog = False
time.sleep(2)

"""
Loop here using screen type to choose renderer and names to fill in cmdtxt - return value is next screen or a tap count
"""

config.backlight.ChangeDutyCycle(config.BrightLevel)
config.CurrentScreen = config.HomeScreen
prevscreen = None
mainchainactive = True
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

pygame.quit()
