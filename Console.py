import config
from config import *
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


"""
Actual Code to Drive Console
"""

config.screen = DisplayScreen.DisplayScreen()
config.ParsedConfigFile = ConfigObj(infile="/home/pi/Console/config.txt")

config.ISYaddr = str(config.ParsedConfigFile.get("ISYaddr",""))
config.ISYuser = str(config.ParsedConfigFile.get("ISYuser",""))
config.ISYpassword = str(config.ParsedConfigFile.get("ISYpassword",""))
config.HomeScreenName = str(config.ParsedConfigFile.get("HomeScreenName",""))
config.HomeScreenTO = int(config.ParsedConfigFile.get("HomeScreenTO",config.HomeScreenTO))


GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
config.backlight = GPIO.PWM(18,1024)
config.backlight.start(100)


config.ConnISY = ISYSetup.ISYsetup()
nodemgr = config.ConnISY.myisy.nodes
programs = config.ConnISY.myisy.programs

config.ConnISY.WalkFolder(nodemgr)
config.ConnISY.EnumeratePrograms(programs)
pygame.fastevent.init()
CurrentScreenInfo = ConfigObjects.MyScreens()

config.toDaemon = Queue()
config.fromDaemon = Queue()
p = Process(target=WatchDaemon.Watcher)
p.daemon = True
p.start()
debugprint(dbgMain, "Spawned watcher as: ", p.pid)


    




"""
Loop here using screen type to choose renderer and names to fill in cmdtxt - return value should be cmdbutindex
"""

config.currentscreen = CurrentScreenInfo.screenlist[config.HomeScreenName]

while 1:
    if config.previousscreen <> config.currentscreen:
        config.previousscreen = config.currentscreen
        config.currentscreen = config.currentscreen.HandleScreen(True)
    else:
        config.currentscreen = config.currentscreen.HandleScreen(False)
        



Tstat = ConnISY.myisy.nodes["22 18 A3 1"]



