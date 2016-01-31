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

import config
from config import debugprint
from configobj import ConfigObj
import PyISY
import ButLayout
import ConfigObjects
import DisplayScreen
import pygame
import RPi.GPIO as GPIO
import ISYSetup
import multiprocessing
from  multiprocessing import Process, Queue
import WatchDaemon
import sys, signal, time, os
import webcolors
wc = webcolors.name_to_rgb

def signal_handler(signal, frame):
    print "Signal: {}".format(signal)
    print "pid: ", os.getpid()
    time.sleep(1)
    pygame.quit()
    print "Console Exiting"
    sys.exit(0)

"""
Actual Code to Drive Console
"""

print "Console Starting pid:", os.getpid()

def display_line(ln):
    global ls
    global scrnpos
    global UtilFont
    l = UtilFont.render(ln, False, wc('white'))
    config.screen.screen.blit(l,(10,scrnpos))
    pygame.display.update()
    scrnpos = scrnpos + ls

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

config.screen = DisplayScreen.DisplayScreen()

UtilFont = pygame.font.SysFont(None,25,False,False)
ls = UtilFont.get_linesize()
scrnpos = 10
config.screen.screen.fill(wc('royalblue'))
display_line(u"Soft ISY Console")
display_line(u"  \u00A9 Kevin Kahn 2016")
display_line("Console Starting")





if len(sys.argv) == 2:
    config.ParsedConfigFile = ConfigObj(infile=sys.argv[1])
else:
    config.ParsedConfigFile = ConfigObj(infile="/home/pi/Console/config.txt")

# Global settings from config file
config.ISYaddr        = str(config.ParsedConfigFile.get("ISYaddr",""))
config.ISYuser        = str(config.ParsedConfigFile.get("ISYuser",""))
config.ISYpassword    = str(config.ParsedConfigFile.get("ISYpassword",""))
config.HomeScreenName = str(config.ParsedConfigFile.get("HomeScreenName",""))
config.HomeScreenTO   = int(config.ParsedConfigFile.get("HomeScreenTO",config.HomeScreenTO))
config.DimLevel       = int(config.ParsedConfigFile.get("DimLevel",config.DimLevel))
config.BrightLevel    = int(config.ParsedConfigFile.get("BrightLevel",config.BrightLevel))
config.DimTO          = int(config.ParsedConfigFile.get("DimTO",config.DimTO))
config.CmdKeyCol      = str(config.ParsedConfigFile.get("CmKeyColor",config.CmdKeyCol))
config.CmdCharCol     = str(config.ParsedConfigFile.get("CmdCharCol",config.CmdCharCol))


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
config.backlight = GPIO.PWM(18,1024)
config.backlight.start(100)

config.ConnISY = ISYSetup.ISYsetup()
nodemgr = config.ConnISY.myisy.nodes
programs = config.ConnISY.myisy.programs
if config.ConnISY.myisy.connected:
    display_line("Connected to ISY")
else:
    display_line("Failed to connect to ISY")
    config.ErrorItems.append("Connection to ISY failed")
    

config.ConnISY.WalkFolder(nodemgr)
config.ConnISY.EnumeratePrograms(programs)
display_line("Enumerated ISY")

pygame.fastevent.init()
CurrentScreenInfo = ConfigObjects.MyScreens()

config.toDaemon = Queue()
config.fromDaemon = Queue()
p = Process(target=WatchDaemon.Watcher)
p.daemon = True

p.start()
debugprint(config.dbgMain, "Spawned watcher as: ", p.pid)

ButLayout.InitButtonFonts()


time.sleep(5)
"""
Loop here using screen type to choose renderer and names to fill in cmdtxt - return value should be cmdbutindex
"""

config.backlight.ChangeDutyCycle(config.BrightLevel)
config.currentscreen = config.HomeScreen
nextscreen = None
prevscreen = None
while 1:
    nextscreen = config.currentscreen.HandleScreen(prevscreen <> config.currentscreen)
    if isinstance(nextscreen, int):
        print "Maint req", nextscreen
        if nextscreen > 7:
            break
        nextscreen = config.HomeScreen
    prevscreen = config.currentscreen
    config.currentscreen = nextscreen
    
        
pygame.quit()
